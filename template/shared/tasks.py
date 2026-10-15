from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task(
    max_retries=5,
    # Falhas transitórias (rede, Google lento, recusa do script) merecem
    # retentativa com backoff; cota diária esgotada falha após as tentativas
    # e fica visível no log do worker.
    autoretry_for=(OSError, RuntimeError),
    retry_backoff=True,
)
def send_email_task(subject, body, to, from_email=None, user_id=None):
    """Envia e-mail pelo backend configurado, fora da requisição HTTP.

    Cadastro e reset enfileiram aqui: o POST não pode segurar o worker da
    web por até APPS_SCRIPT_TIMEOUT segundos nem falhar porque o Google
    está lento. ``user_id`` — só o cadastro passa — registra no usuário a
    falha final do e-mail de ativação: entre o gate de cota do formulário
    e este task, outra requisição pode consumir a última cota da fila, o
    usuário vê "enviamos" e o link nunca chega. Sem o registro, a conta
    órfã só existiria no log do worker.
    """
    try:
        sent = send_mail(subject, body, from_email or settings.DEFAULT_FROM_EMAIL, to)
    except (OSError, RuntimeError):
        if user_id is not None and _retries_exhausted():
            _set_activation_email_failed(user_id, True)
        raise
    if user_id is not None:
        _set_activation_email_failed(user_id, False)
    return sent


def _retries_exhausted():
    """True na última tentativa permitida — depois dela não há reenvio."""
    return send_email_task.request.retries >= send_email_task.max_retries


def _set_activation_email_failed(user_id, failed):
    """Acende/apaga o registro de falha; só escreve quando muda.

    Import local: accounts importa shared (tasks), e o caminho de volta
    no topo do módulo criaria ciclo na carga do app.
    """
    from accounts.models import User

    User.objects.filter(pk=user_id, activation_email_failed=not failed).update(
        activation_email_failed=failed
    )
