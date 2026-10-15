from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from shared.tasks import send_email_task

User = get_user_model()


class ActivationEmailFailureRecordTestCase(TestCase):
    """O registro de falha acende só quando os retries esgotam.

    Entre o gate de cota do formulário e este task, outra requisição pode
    consumir a última cota da fila: o usuário viu "enviamos", o link
    nunca chega. Sem a flag no usuário, a conta órfã só existiria no log
    do worker. Marcar durante o backoff seria registro piscando no admin
    — a falha ainda pode se resolver sozinha.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            'sem-link@exemplo.com',
            'senha-forte-123',
            first_name='Sem',
            last_name='Link',
        )

    def test_sucesso_apaga_o_registro_de_falha(self):
        User.objects.filter(pk=self.user.pk).update(activation_email_failed=True)

        with mock.patch('shared.tasks.send_mail', return_value=1):
            send_email_task.run('assunto', 'corpo', [self.user.email], user_id=self.user.pk)

        self.user.refresh_from_db()
        self.assertFalse(self.user.activation_email_failed)

    def test_falha_na_ultima_tentativa_acende_o_registro(self):
        send_email_task.push_request(retries=send_email_task.max_retries)
        try:
            with (
                mock.patch('shared.tasks.send_mail', side_effect=RuntimeError('cota esgotada')),
                self.assertRaises(RuntimeError),
            ):
                send_email_task.run('assunto', 'corpo', [self.user.email], user_id=self.user.pk)
        finally:
            send_email_task.pop_request()

        self.user.refresh_from_db()
        self.assertTrue(self.user.activation_email_failed)

    def test_falha_com_retentativas_restantes_nao_acende(self):
        send_email_task.push_request(retries=0)
        try:
            with (
                mock.patch('shared.tasks.send_mail', side_effect=OSError('google lento')),
                self.assertRaises(OSError),
            ):
                send_email_task.run('assunto', 'corpo', [self.user.email], user_id=self.user.pk)
        finally:
            send_email_task.pop_request()

        self.user.refresh_from_db()
        self.assertFalse(self.user.activation_email_failed)

    def test_reset_sem_user_id_falha_sem_registrar_usuario(self):
        # o reset não registra: sem model de solicitação, a falha segue
        # só no log do worker
        send_email_task.push_request(retries=send_email_task.max_retries)
        try:
            with (
                mock.patch('shared.tasks.send_mail', side_effect=RuntimeError('x')),
                self.assertRaises(RuntimeError),
            ):
                send_email_task.run('assunto', 'corpo', ['alguem@exemplo.com'])
        finally:
            send_email_task.pop_request()

        self.assertFalse(User.objects.filter(activation_email_failed=True).exists())
