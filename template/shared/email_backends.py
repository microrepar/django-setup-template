import json
import logging
import sys
from email.errors import HeaderParseError
from email.header import decode_header, make_header
from urllib import request as urllib_request

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

# Probe da cota no caminho da requisição (gate do cadastro/reset): curto
# para não pendurar o POST do usuário. Falha ou resposta ilegível conta
# como "há cota" (fail-open) — a checagem de verdade acontece no task,
# com o timeout completo, imediatamente antes do POST.
QUOTA_PROBE_TIMEOUT = 2


def script_urls():
    """URLs da fila APPS_SCRIPT_URL, em ordem de prioridade.

    A cota diária do MailApp é por conta Google que executa o script,
    então cada URL da fila deve ser um deploy do script em uma conta
    diferente — a fila multiplica a capacidade diária. Um valor único
    continua funcionando como sempre funcionou.
    """
    return [url.strip() for url in settings.APPS_SCRIPT_URL.split(",") if url.strip()]


def remaining_quota(url, timeout):
    """``rateLimit`` reportado pelo doGet do script; None se ilegível."""
    request_ = urllib_request.Request(url, method="GET")
    try:
        # Mesmo 302 do POST: o urllib segue o redirecionamento sozinho.
        with urllib_request.urlopen(request_, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    try:
        result = json.loads(body)
    except ValueError:
        return None
    if isinstance(result, dict) and isinstance(result.get("rateLimit"), int):
        return result["rateLimit"]
    return None


def quota_chain_available(recipients=1, timeout=QUOTA_PROBE_TIMEOUT):
    """True quando a fila do Apps Script tem cota para os destinatários.

    Gate síncrono do cadastro e do reset de senha: sem cota em nenhuma
    URL, o formulário recusa na hora — em vez de responder "enviamos" e
    deixar o e-mail morrer no worker. Só se aplica ao backend do Apps
    Script: console/SMTP não têm cota diária consultável (e o runner de
    testes troca o backend por locmem, ficando fora daqui sem mocks).
    Telemetria ausente — fila não configurada, GET lento ou ilegível —
    conta como cota: telemetria não pode barrar o usuário.
    """
    if settings.EMAIL_BACKEND != "shared.email_backends.AppsScriptEmailBackend":
        return True
    urls = script_urls()
    if not urls:
        return True
    for url in urls:
        remaining = remaining_quota(url, timeout)
        if remaining is None or remaining >= recipients:
            return True
    return False


class ConsoleEmailBackend(BaseEmailBackend):
    """Backend de e-mail que imprime a mensagem decodificada no console.

    O backend de console do Django escreve a mensagem MIME bruta, com o
    corpo em UTF-8 codificado em base64 (acentos ilegíveis). Este backend
    decodifica os cabeçalhos e o corpo e imprime o texto legível.
    """

    def __init__(self, *args, **kwargs):
        self.stream = kwargs.pop("stream", sys.stdout)
        super().__init__(*args, **kwargs)

    def send_messages(self, email_messages):
        count = 0
        for message in email_messages:
            self.write_message(message)
            count += 1
        self.stream.flush()
        return count

    def write_message(self, email_message):
        msg = email_message.message()
        sep = "=" * 79
        self.stream.write(f"{sep}\n")
        self.stream.write(f"From: {self._decode_header(msg, 'From')}\n")
        self.stream.write(f"To: {self._decode_header(msg, 'To')}\n")
        self.stream.write(f"Subject: {self._decode_header(msg, 'Subject')}\n")
        self.stream.write(f"{'-' * 79}\n")
        self.stream.write(self._extract_body(msg))
        self.stream.write(f"\n{sep}\n")

    @staticmethod
    def _decode_header(msg, name):
        value = msg.get(name, "")
        if not value:
            return ""
        try:
            return str(make_header(decode_header(value)))
        except (HeaderParseError, UnicodeError):
            return value

    @staticmethod
    def _extract_body(msg):
        """Decodifica a primeira parte text/plain da mensagem."""
        parts = msg.walk() if msg.is_multipart() else [msg]
        for part in parts:
            if part.is_multipart():
                continue
            if part.get_content_type() != "text/plain":
                continue
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
        return ""


class AppsScriptEmailBackend(BaseEmailBackend):
    """Backend que envia e-mails por um Web App do Google Apps Script.

    Em vez de falar SMTP com um provedor (SendGrid etc.), faz um POST JSON
    ``{to, subject, body}`` para a URL do script, que chama MailApp.sendEmail
    — o mesmo contrato do serviço de e-mail do projeto Imprensa, portanto o
    mesmo script atende os dois projetos. O campo ``body`` prefere a
    alternativa HTML da mensagem; ``cc``/``bcc`` só vão no payload quando
    preenchidos. Um token opcional (``APPS_SCRIPT_TOKEN``) viaja no payload
    como ``token`` e deve ser validado pelo doPost do script. ``APPS_SCRIPT_URL``
    aceita uma fila de URLs separadas por vírgula (cada deploy em uma conta
    Google, para cotas independentes): o POST vai para a primeira com cota
    para o lote. Antes dele, consulta o doGet de cada URL pela cota restante
    do MailApp: esgotá-la não gera erro no envio (200/{"ok": true} e o
    e-mail não sai), então a checagem prévia é o único ponto de falha visível.
    """

    def send_messages(self, email_messages):
        urls = script_urls()
        if not urls:
            if self.fail_silently:
                return 0
            raise ImproperlyConfigured(
                "APPS_SCRIPT_URL não configurada. Defina a(s) URL(s) do Web "
                "App do Apps Script no .env, separadas por vírgula (ver bloco "
                "Apps Script no .env.example)."
            )

        # Cota esgotada não vira erro no POST (o MailApp engole o envio em
        # silêncio), então checar antes é a única chance de falhar alto.
        url = self._url_for_batch(urls, email_messages)
        if url is None:
            return 0
        count = 0
        for message in email_messages:
            if self._send(message, url):
                count += 1
        return count

    def _send(self, message, url):
        payload = {
            "to": ", ".join(message.to),
            "subject": message.subject,
            "body": self._extract_body(message),
        }
        if message.cc:
            payload["cc"] = ", ".join(message.cc)
        if message.bcc:
            payload["bcc"] = ", ".join(message.bcc)
        # O token viaja no payload, não em cabeçalho: o doPost de um Web App
        # do Apps Script não tem acesso aos cabeçalhos HTTP da requisição.
        if settings.APPS_SCRIPT_TOKEN:
            payload["token"] = settings.APPS_SCRIPT_TOKEN

        request_ = urllib_request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            # O /exec do Apps Script responde 302 para uma URL temporária;
            # o urllib segue o redirecionamento sozinho.
            with urllib_request.urlopen(
                request_, timeout=settings.APPS_SCRIPT_TIMEOUT
            ) as response:
                body = response.read().decode("utf-8", errors="replace")
        except OSError as error:
            # URLError, HTTPError e TimeoutError derivam de OSError: a
            # requisição falhou (DNS, timeout, HTTP >= 400...).
            return self._fail(message, payload["to"], error, error)

        # O script de referência (.docs/apps_script_email.gs) responde JSON
        # {"ok": true} no sucesso e {"error": ...} na recusa (token
        # inválido, campos ausentes). Corpo sem "error" — HTTP 200, script
        # antigo da Imprensa — continua sendo sucesso.
        script_error = self._script_error(body)
        if script_error:
            return self._fail(message, payload["to"], script_error)
        return True

    def _url_for_batch(self, urls, email_messages):
        """Primeira URL da fila cuja cota cobre o lote; None se todas esgotadas.

        O MailApp esgota a cota em silêncio: o POST continua devolvendo
        200/{"ok": true} e o e-mail simplesmente não sai. O doGet do script
        (.docs/apps_script_email.gs) expõe MailApp.getRemainingDailyQuota()
        no campo ``rateLimit``. O roteamento é stateless, sempre do topo:
        quando a cota da primeira URL reseta (meia-noite PT), os envios
        voltam para ela sozinhos, sem estado para invalidar. ``rateLimit``
        ilegível (script antigo sem doGet, corpo que não é JSON, erro de
        rede no GET) usa a URL mesmo assim — telemetria ausente não pode
        bloquear o e-mail. Cota parcial pula a URL inteira: o lote não se
        divide entre remetentes.
        """
        recipients = sum(len(m.to) + len(m.cc) + len(m.bcc) for m in email_messages)
        exhausted = []
        for url in urls:
            remaining = remaining_quota(url, settings.APPS_SCRIPT_TIMEOUT)
            if remaining is None or remaining >= recipients:
                if exhausted:
                    logger.warning(
                        "Apps Script: cota esgotada em %s; roteando para %s",
                        ", ".join(exhausted),
                        url,
                    )
                return url
            exhausted.append(f"{url} ({remaining} restante(s))")
        reason = (
            f"cota diária do MailApp esgotada em toda a fila: {', '.join(exhausted)}"
        )
        logger.error("Apps Script: %s", reason)
        if self.fail_silently:
            return None
        raise RuntimeError(f"Apps Script rejeitou o envio: {reason}")

    def _fail(self, message, to, reason, exception=None):
        logger.error(
            'Apps Script: falha ao enviar "%s" para %s: %s', message.subject, to, reason
        )
        if self.fail_silently:
            return False
        if exception is not None:
            raise exception
        raise RuntimeError(f"Apps Script rejeitou o envio: {reason}")

    @staticmethod
    def _script_error(body):
        """Mensagem de erro reportada pelo script no corpo da resposta."""
        try:
            result = json.loads(body)
        except ValueError:
            return None
        if isinstance(result, dict):
            return result.get("error")
        return None

    @staticmethod
    def _extract_body(message):
        """Prefere a alternativa HTML; sem ela, o corpo em texto puro.

        O contrato do Apps Script tem um único campo ``body``, tratado como
        htmlBody pelo script (mesmo formato do projeto Imprensa).
        """
        for content, mimetype in getattr(message, "alternatives", []):
            if mimetype == "text/html":
                return content
        return message.body or ""
