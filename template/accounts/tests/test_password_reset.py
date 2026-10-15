import re
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

OLD_PASSWORD = 'senha-antiga-123'
NEW_PASSWORD = 'senha-nova-segura-456'


class PasswordResetFlowTestCase(TestCase):
    """Fluxo completo: pedido por e-mail, link com token, nova senha passando a valer."""

    def setUp(self):
        self.user = User.objects.create_user(
            'Usuario@Exemplo.com', OLD_PASSWORD, first_name='Usuário', last_name='de Teste'
        )

    @staticmethod
    def extract_reset_path(body):
        match = re.search(r'/accounts/reset/(?P<uidb64>[^/]+)/(?P<token>[^/]+)/', body)
        if match is None:
            raise AssertionError('o e-mail de redefinição deve conter o link com uid e token')
        return match.group(0)

    def request_reset(self, email='usuario@exemplo.com'):
        return self.client.post(reverse('password_reset'), {'email': email})

    @mock.patch('accounts.forms.send_email_task')
    def test_reset_email_e_enfileirado_no_celery(self, task):
        # o pedido de reset responde na hora; o envio vai para a fila
        self.request_reset()

        task.delay.assert_called_once()
        _subject, _body, to = task.delay.call_args[0]
        self.assertEqual(to, ['usuario@exemplo.com'])

    @mock.patch('accounts.forms.quota_chain_available', return_value=False)
    @mock.patch('accounts.forms.send_email_task')
    def test_reset_recusado_quando_a_fila_de_envio_esgota(self, task, _gate):
        # a recusa é igual existindo ou não a conta: cota é ortogonal, a
        # mensagem não vaza existência de e-mail
        response = self.request_reset()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'capacidade diária de envios')
        task.delay.assert_not_called()
        self.assertEqual(len(mail.outbox), 0)

    def open_reset_form(self):
        """Abre o formulário a partir do link do e-mail.

        O Django redireciona a URL com o token real para uma URL sem token
        (``set-password``), guardando o token na sessão — evita vazamento do
        token via cabeçalho Referer.
        """
        reset_path = self.extract_reset_path(mail.outbox[0].body)
        response = self.client.get(reset_path)
        form_url = response.url
        response = self.client.get(form_url)
        self.assertTrue(response.context['validlink'])
        return form_url

    def test_full_reset_flow(self):
        # 1. pedido com o e-mail em caixa diferente da cadastrada também recebe o link
        response = self.request_reset()
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Redefinição de senha', mail.outbox[0].subject)

        # 2. o link do e-mail abre o formulário de nova senha
        form_url = self.open_reset_form()

        # 3. definir a nova senha
        response = self.client.post(
            form_url, {'new_password1': NEW_PASSWORD, 'new_password2': NEW_PASSWORD}
        )
        self.assertRedirects(response, reverse('password_reset_complete'))

        # 4. a senha antiga deixa de valer; a nova autentica no login
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password(OLD_PASSWORD))
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertTrue(self.client.login(email='usuario@exemplo.com', password=NEW_PASSWORD))

    def test_unknown_email_does_not_reveal_registered_accounts(self):
        # Mesma resposta de sucesso, nenhum e-mail enviado.
        response = self.request_reset(email='desconhecido@exemplo.com')
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_link_is_single_use(self):
        self.request_reset()
        form_url = self.open_reset_form()
        self.client.post(
            form_url, {'new_password1': NEW_PASSWORD, 'new_password2': NEW_PASSWORD}
        )

        # a senha mudou: o token da sessão não vale mais, o link é inutilizável
        response = self.client.get(form_url)
        self.assertFalse(response.context['validlink'])
