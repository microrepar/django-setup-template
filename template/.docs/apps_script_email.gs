/**
 * Web App de envio de e-mails — Google Apps Script (MailApp).
 *
 * Contrato (compatível com o serviço de e-mail do projeto Imprensa):
 *   POST {to, subject, body, cc?, bcc?, token?}
 *   - body é entregue como htmlBody (aceita texto puro também)
 *   - to/cc/bcc são strings com destinatários separados por vírgula
 *   - token, quando AUTH_TOKEN estiver definido, precisa bater — é a
 *     autenticação da chamada (Web Apps não enxergam cabeçalhos HTTP,
 *     por isso o token viaja no payload)
 *
 * Respostas (sempre HTTP 200 — limitação do ContentService):
 *   {"ok": true}              envio feito
 *   {"error": "<motivo>"}     recusa (o backend Django entende como falha)
 *
 *   GET (sem autenticação — expõe apenas a cota restante):
 *   {"status": "success", "message": ..., "rateLimit": N}
 *   - rateLimit é MailApp.getRemainingDailyQuota(): destinatários que
 *     ainda podem receber hoje. O backend Django consulta antes de cada
 *     envio porque o MailApp esgota a cota em silêncio — o POST segue
 *     respondendo {"ok": true} e o e-mail não sai. Script sem doGet
 *     (o antigo da Imprensa) não bloqueia o envio: sem rateLimit
 *     legível, o backend envia mesmo assim.
 *
 * Como publicar:
 *   1. script.google.com > Novo projeto > cole este código;
 *   2. troque AUTH_TOKEN por um segredo forte (o mesmo valor de
 *      APPS_SCRIPT_TOKEN no .env do Django; vazio desativa a checagem);
 *   3. Implantar > Nova implantação > Tipo: app da Web
 *      "Executar como: Eu" e "Quem tem acesso: Qualquer pessoa";
 *   4. a URL /exec do deploy é a APPS_SCRIPT_URL no .env.
 *   Reimplante (Gerenciar implantações > Editar > Nova versão) a cada
 *   mudança neste código.
 *
 * Cotas do MailApp: 100 destinatários/dia (Gmail comum), 1.500/dia
 * (Google Workspace). A cota é por conta Google que executa o script:
 * para mais capacidade, implante este mesmo script (mesmo AUTH_TOKEN)
 * em outras contas e liste as URLs do /exec no APPS_SCRIPT_URL do .env,
 * separadas por vírgula — esgotada a cota da primeira URL, o backend
 * roteia o envio para a próxima da fila.
 */

const AUTH_TOKEN = '<SEU_TOKEN>';

function doPost(e) {
  try {
    const payload = JSON.parse(e.postData.contents);

    if (AUTH_TOKEN && payload.token !== AUTH_TOKEN) {
      return json_({ error: 'unauthorized' });
    }
    if (!payload.to || !payload.subject || !payload.body) {
      return json_({ error: 'bad_request: to, subject e body são obrigatórios' });
    }

    const options = { htmlBody: payload.body };
    if (payload.cc) {
      options.cc = payload.cc;
    }
    if (payload.bcc) {
      options.bcc = payload.bcc;
    }
    MailApp.sendEmail(payload.to, payload.subject, payload.body, options);
    return json_({ ok: true });
  } catch (error) {
    return json_({ error: String(error) });
  }
}

function doGet(e) {
  const restante = MailApp.getRemainingDailyQuota();
  return json_({
    status: 'success',
    message: 'API está funcionando! Você ainda pode enviar para ' + restante + ' destinatários hoje.',
    rateLimit: restante
  });
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
