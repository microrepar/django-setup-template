import json
from unittest import mock
from urllib.error import HTTPError, URLError

from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.test import SimpleTestCase, override_settings

from shared.email_backends import (
    QUOTA_PROBE_TIMEOUT,
    AppsScriptEmailBackend,
    quota_chain_available,
)

SCRIPT_URL = "https://script.google.com/macros/s/SCRIPT_ID/exec"
SCRIPT_URL_2 = "https://script.google.com/macros/s/OUTRO_SCRIPT_ID/exec"


def ok_response(body=b'{"ok": true}'):
    """Resposta de urlopen bem-sucedida (200) com o corpo dado.

    ``__enter__`` devolve o próprio mock para que ``with urlopen(...) as r``
    entregue esta resposta (e o ``r.read()`` do backend veja o corpo real).
    """
    response = mock.MagicMock()
    response.status = 200
    response.read.return_value = body
    response.__enter__.return_value = response
    return response


def sent_request(urlopen_mock):
    """A urllib.Request do POST de envio (ignora os GETs do probe de cota)."""
    for call in urlopen_mock.call_args_list:
        request_obj = call.args[0]
        if request_obj.get_method() == "POST":
            return request_obj, json.loads(request_obj.data)
    raise AssertionError("nenhum POST de envio foi feito")


def quota_response(remaining):
    """Resposta do doGet do script com a cota restante do MailApp."""
    body = json.dumps(
        {
            "status": "success",
            "message": f"Você ainda pode enviar para {remaining} destinatários hoje.",
            "rateLimit": remaining,
        }
    )
    return ok_response(body.encode())


@override_settings(APPS_SCRIPT_URL=SCRIPT_URL, APPS_SCRIPT_TOKEN="")
class AppsScriptEmailBackendTestCase(SimpleTestCase):
    """O backend precisa falar o contrato {to, subject, body} do Web App.

    O mesmo Apps Script do projeto Imprensa deve atender os dois projetos
    sem alteração: se este backend mudar o formato do POST, o script deixa
    de funcionar para quem já está em produção. Erros seguem o contrato do
    Django: levantam exceção, a menos que fail_silently esteja ativo.
    """

    def make_message(self, **kwargs):
        message = EmailMultiAlternatives(
            "Redefinição de senha",
            "acesse o link: http://exemplo.com/reset",
            to=["usuario@exemplo.com", "outro@exemplo.com"],
            **kwargs,
        )
        message.attach_alternative(
            '<p>acesse o <a href="...">link</a></p>', "text/html"
        )
        return message

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_payload_segue_contrato_do_apps_script(self, urlopen):
        urlopen.return_value = ok_response()
        sent = self.backend().send_messages([self.make_message()])

        request_obj, payload = sent_request(urlopen)
        self.assertEqual(sent, 1)
        self.assertEqual(request_obj.full_url, SCRIPT_URL)
        self.assertEqual(request_obj.get_method(), "POST")
        # chaves exatamente as do contrato da Imprensa (cc/bcc ausentes ficam de fora)
        self.assertEqual(set(payload), {"to", "subject", "body"})
        self.assertEqual(payload["to"], "usuario@exemplo.com, outro@exemplo.com")
        self.assertEqual(payload["subject"], "Redefinição de senha")
        # a alternativa HTML é preferida: o script a entrega como htmlBody
        self.assertEqual(payload["body"], '<p>acesse o <a href="...">link</a></p>')

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_sem_alternativa_html_o_corpo_e_texto_puro(self, urlopen):
        urlopen.return_value = ok_response()
        message = EmailMessage("assunto", "corpo simples", to=["a@exemplo.com"])

        self.backend().send_messages([message])

        _, payload = sent_request(urlopen)
        self.assertEqual(payload["body"], "corpo simples")

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_cc_e_bcc_entram_no_payload_quando_preenchidos(self, urlopen):
        urlopen.return_value = ok_response()
        message = self.make_message(
            cc=["copia@exemplo.com"], bcc=["oculto@exemplo.com"]
        )

        self.backend().send_messages([message])

        _, payload = sent_request(urlopen)
        self.assertEqual(payload["cc"], "copia@exemplo.com")
        self.assertEqual(payload["bcc"], "oculto@exemplo.com")

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_token_viaja_no_payload_nao_no_cabecalho(self, urlopen):
        # o doPost de um Web App não enxerga cabeçalhos HTTP: o token só
        # chega ao script se for parte do JSON do POST
        urlopen.return_value = ok_response()
        with override_settings(APPS_SCRIPT_TOKEN="segredo-do-script"):
            self.backend().send_messages([self.make_message()])

        request_obj, payload = sent_request(urlopen)
        self.assertEqual(payload["token"], "segredo-do-script")
        self.assertIsNone(request_obj.get_header("Authorization"))

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_sem_token_payload_nao_tem_chave_token(self, urlopen):
        urlopen.return_value = ok_response()
        self.backend().send_messages([self.make_message()])

        _, payload = sent_request(urlopen)
        self.assertNotIn("token", payload)

    def test_url_nao_configurada_dispara_improperly_configured(self):
        with (
            override_settings(APPS_SCRIPT_URL=""),
            self.assertRaisesMessage(ImproperlyConfigured, "APPS_SCRIPT_URL"),
        ):
            self.backend().send_messages([self.make_message()])

    def test_url_nao_configurada_e_silenciosa_retorna_zero(self):
        with override_settings(APPS_SCRIPT_URL=""):
            sent = self.backend(fail_silently=True).send_messages([self.make_message()])
        self.assertEqual(sent, 0)

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_erro_http_dispara_excecao(self, urlopen):
        urlopen.side_effect = HTTPError(SCRIPT_URL, 500, "Server Error", None, None)

        with self.assertRaises(HTTPError):
            self.backend().send_messages([self.make_message()])

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_erro_reportado_no_corpo_da_resposta_dispara_excecao(self, urlopen):
        # o script de referência não devolve HTTP de erro (o ContentService
        # do Apps Script sempre responde 200): a recusa chega como
        # {"error": ...} no corpo
        urlopen.return_value = ok_response(b'{"error": "unauthorized"}')

        with self.assertRaisesMessage(RuntimeError, "unauthorized"):
            self.backend().send_messages([self.make_message()])

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_corpo_sem_json_e_sucesso_para_scripts_antigos(self, urlopen):
        # compatibilidade com o script da Imprensa, que não fala JSON:
        # HTTP 200 sem "error" no corpo não pode virar falha
        urlopen.return_value = ok_response(b"ok")

        sent = self.backend().send_messages([self.make_message()])
        self.assertEqual(sent, 1)

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_cota_zerada_bloqueia_o_envio(self, urlopen):
        # o MailApp esgota a cota em silêncio (200/{"ok": true} e o e-mail
        # não sai): sem essa checagem, o e-mail se perderia como sucesso
        urlopen.side_effect = [quota_response(0)]

        with self.assertRaisesMessage(RuntimeError, "cota diária"):
            self.backend().send_messages([self.make_message()])
        self.assertEqual(urlopen.call_count, 1)  # só o GET; o POST não acontece
        self.assertEqual(urlopen.call_args[0][0].get_method(), "GET")

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_cota_menor_que_o_lote_bloqueia_o_envio(self, urlopen):
        # a cota conta destinatários, não mensagens: resta 1, o lote pede 2
        urlopen.side_effect = [quota_response(1)]

        with self.assertRaisesMessage(RuntimeError, "cota diária"):
            self.backend().send_messages([self.make_message()])
        self.assertEqual(urlopen.call_count, 1)

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_cota_suficiente_deixa_o_post_acontecer(self, urlopen):
        urlopen.side_effect = [quota_response(2), ok_response()]

        sent = self.backend().send_messages([self.make_message()])

        self.assertEqual(sent, 1)
        methods = [call.args[0].get_method() for call in urlopen.call_args_list]
        self.assertEqual(methods, ["GET", "POST"])

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_cota_zerada_com_fail_silently_retorna_zero(self, urlopen):
        urlopen.side_effect = [quota_response(0)]

        sent = self.backend(fail_silently=True).send_messages([self.make_message()])

        self.assertEqual(sent, 0)
        self.assertEqual(urlopen.call_count, 1)

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_doget_sem_ratelimit_nao_bloqueia_script_antigo(self, urlopen):
        # o script antigo da Imprensa não tem doGet: o GET devolve {"ok":
        # true} (ou HTML), sem rateLimit legível — o envio segue mesmo assim
        urlopen.side_effect = [ok_response(), ok_response()]

        sent = self.backend().send_messages([self.make_message()])

        self.assertEqual(sent, 1)

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_falha_no_get_da_cota_nao_bloqueia_o_envio(self, urlopen):
        # a checagem de cota é telemetria, não autenticação: se o GET falha,
        # o POST ainda é tentado (e é ele que decide o destino do envio)
        urlopen.side_effect = [URLError("google fora do ar"), ok_response()]

        sent = self.backend().send_messages([self.make_message()])

        self.assertEqual(sent, 1)

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_url_esgotada_roteia_o_envio_para_a_proxima_da_fila(self, urlopen):
        # a cota é por conta Google: fila de URLs = capacidade somada. A
        # primeira esgotou, o POST inteiro vai para a segunda
        with override_settings(APPS_SCRIPT_URL=f"{SCRIPT_URL},{SCRIPT_URL_2}"):
            urlopen.side_effect = [quota_response(0), quota_response(5), ok_response()]

            sent = self.backend().send_messages([self.make_message()])

        self.assertEqual(sent, 1)
        request_obj, _payload = sent_request(urlopen)
        self.assertEqual(request_obj.full_url, SCRIPT_URL_2)

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_urls_da_fila_sao_normalizadas_sem_espacos(self, urlopen):
        with override_settings(APPS_SCRIPT_URL=f"  {SCRIPT_URL} ,  {SCRIPT_URL_2}  "):
            urlopen.side_effect = [quota_response(0), quota_response(2), ok_response()]

            self.backend().send_messages([self.make_message()])

        request_obj, _payload = sent_request(urlopen)
        self.assertEqual(request_obj.full_url, SCRIPT_URL_2)

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_fila_inteira_esgotada_dispara_excecao_listando_as_cotas(self, urlopen):
        with override_settings(APPS_SCRIPT_URL=f"{SCRIPT_URL},{SCRIPT_URL_2}"):
            urlopen.side_effect = [quota_response(0), quota_response(1)]

            with self.assertRaisesMessage(RuntimeError, "toda a fila"):
                self.backend().send_messages([self.make_message()])
        self.assertEqual(urlopen.call_count, 2)  # só GETs, nenhum POST

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_fila_inteira_esgotada_e_silenciosa_retorna_zero(self, urlopen):
        with override_settings(APPS_SCRIPT_URL=f"{SCRIPT_URL},{SCRIPT_URL_2}"):
            urlopen.side_effect = [quota_response(0), quota_response(1)]

            sent = self.backend(fail_silently=True).send_messages([self.make_message()])
        self.assertEqual(sent, 0)
        self.assertEqual(urlopen.call_count, 2)

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_ratelimit_ilegivel_usa_a_url_mesmo_com_proxima_disponivel(self, urlopen):
        # telemetria ausente não é sinal de esgotamento: sem rateLimit
        # legível o envio segue pela URL, não pula para a próxima
        with override_settings(APPS_SCRIPT_URL=f"{SCRIPT_URL},{SCRIPT_URL_2}"):
            urlopen.side_effect = [ok_response(b"ok"), ok_response()]

            sent = self.backend().send_messages([self.make_message()])

        self.assertEqual(sent, 1)
        request_obj, _payload = sent_request(urlopen)
        self.assertEqual(request_obj.full_url, SCRIPT_URL)

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_fail_silently_conta_apenas_os_envios_bem_sucedidos(self, urlopen):
        # a primeira chamada é o GET da cota (ok, sem rateLimit); o primeiro
        # POST falha (HTTP 500), o segundo sai: o retorno do send_messages é
        # a contagem de sucessos, contrato do Django
        ok = ok_response()
        urlopen.side_effect = [
            ok_response(),
            HTTPError(SCRIPT_URL, 500, "Server Error", None, None),
            ok,
        ]

        sent = self.backend(fail_silently=True).send_messages(
            [self.make_message(), self.make_message()]
        )
        self.assertEqual(sent, 1)

    @staticmethod
    def backend(fail_silently=False):
        return AppsScriptEmailBackend(fail_silently=fail_silently)


@override_settings(
    EMAIL_BACKEND="shared.email_backends.AppsScriptEmailBackend",
    APPS_SCRIPT_URL=f"{SCRIPT_URL},{SCRIPT_URL_2}",
    APPS_SCRIPT_TOKEN="",
)
class QuotaChainAvailableTestCase(SimpleTestCase):
    """Gate síncrono do cadastro/reset: decide se a fila ainda tem cota."""

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_com_cota_na_primeira_url_retorna_true(self, urlopen):
        urlopen.return_value = quota_response(5)

        self.assertTrue(quota_chain_available())
        # o gate roda dentro do POST do usuário: probe curto, não o timeout
        # completo do backend
        self.assertEqual(urlopen.call_args[1]["timeout"], QUOTA_PROBE_TIMEOUT)

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_primeira_esgotada_segunda_com_cota_retorna_true(self, urlopen):
        urlopen.side_effect = [quota_response(0), quota_response(1)]

        self.assertTrue(quota_chain_available())

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_fila_inteira_esgotada_retorna_false(self, urlopen):
        urlopen.side_effect = [quota_response(0), quota_response(0)]

        self.assertFalse(quota_chain_available())

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_telemetria_ilegivel_conta_como_cota(self, urlopen):
        # script antigo sem doGet: HTML sem rateLimit legível não pode
        # barrar o usuário no cadastro
        urlopen.return_value = ok_response(b"<html>erro</html>")

        self.assertTrue(quota_chain_available())

    @mock.patch("shared.email_backends.urllib_request.urlopen")
    def test_erro_de_rede_no_probe_conta_como_cota(self, urlopen):
        urlopen.side_effect = URLError("google fora do ar")

        self.assertTrue(quota_chain_available())

    def test_backend_sem_cota_diaria_passa_sem_probe(self):
        # console/SMTP (e o locmem dos testes) não têm cota consultável: o
        # gate é exclusivo do backend do Apps Script
        with (
            mock.patch("shared.email_backends.urllib_request.urlopen") as urlopen,
            override_settings(
                EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
            ),
        ):
            self.assertTrue(quota_chain_available())
        urlopen.assert_not_called()
