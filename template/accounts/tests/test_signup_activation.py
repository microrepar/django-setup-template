import re
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.tokens import activation_token_generator

User = get_user_model()

SIGNUP_DATA = {
    'email': 'novo@exemplo.com',
    'first_name': 'Nova',
    'last_name': 'Pessoa',
    'password1': 'senha-forte-789',
    'password2': 'senha-forte-789',
}


class SignupActivationFlowTestCase(TestCase):
    """O cadastro só se completa com a posse do e-mail comprovada pelo link.

    Sem essa checagem, qualquer pessoa cria conta com o e-mail de outra e
    fica logada nela — o e-mail de ativação é a prova de posse.
    """

    def test_signup_nao_loga_e_envia_email_de_ativacao(self):
        response = self.client.post(reverse('signup'), SIGNUP_DATA)

        self.assertRedirects(response, reverse('activation_sent'))
        user = User.objects.get(email='novo@exemplo.com')
        self.assertFalse(user.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['novo@exemplo.com'])
        self.assertIn('Confirme', mail.outbox[0].subject)

    @mock.patch('accounts.views.send_email_task')
    def test_activation_email_e_enfileirado_no_celery(self, task):
        # o POST do cadastro não pode segurar a requisição esperando o
        # Google: o envio vai para a fila do Celery
        self.client.post(reverse('signup'), SIGNUP_DATA)

        task.delay.assert_called_once()
        subject, _body, to = task.delay.call_args[0]
        self.assertEqual(to, ['novo@exemplo.com'])
        self.assertIn('Confirme', subject)

    @mock.patch('accounts.forms.quota_chain_available', return_value=False)
    @mock.patch('accounts.views.send_email_task')
    def test_signup_recusado_quando_a_fila_de_envio_esgota(self, task, _gate):
        # sem cota na fila, a conta nem nasce: cadastro sem e-mail de
        # ativação é conta morta — e o usuário fica sabendo que o limite
        # é do sistema, não dele
        response = self.client.post(reverse('signup'), SIGNUP_DATA)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'capacidade diária de cadastros')
        self.assertEqual(User.objects.count(), 0)
        task.delay.assert_not_called()

    def test_link_de_ativacao_confirma_o_email(self):
        self.client.post(reverse('signup'), SIGNUP_DATA)
        match = re.search(r'/accounts/activate/[^/]+/[^/\s]+/', mail.outbox[0].body)
        self.assertIsNotNone(match, 'o e-mail de ativação deve conter o link com uid e token')

        response = self.client.get(match.group(0))

        self.assertTrue(response.context['validlink'])
        user = User.objects.get(email='novo@exemplo.com')
        self.assertTrue(user.email_verified)

    def test_link_de_ativacao_e_de_uso_unico(self):
        # um link de ativação vale exatamente uma confirmação: a verificação
        # incrementa o nonce, que entra no hash — o link usado morre
        self.client.post(reverse('signup'), SIGNUP_DATA)
        match = re.search(r'/accounts/activate/[^/]+/[^/\s]+/', mail.outbox[0].body)

        primeira = self.client.get(match.group(0))
        self.assertTrue(primeira.context['validlink'])

        segunda = self.client.get(match.group(0))
        self.assertFalse(segunda.context['validlink'])

    def test_token_novo_sobrevive_ao_login_e_o_usado_morre(self):
        # o login muda o last_login; o token de ativação não pode embutir
        # esse valor (o gerador padrão o embutiria e o link morreria no
        # primeiro login)
        self.client.post(reverse('signup'), SIGNUP_DATA)
        match = re.search(r'/accounts/activate/[^/]+/[^/\s]+/', mail.outbox[0].body)
        self.client.get(match.group(0))  # ativa
        self.assertTrue(
            self.client.login(email='novo@exemplo.com', password=SIGNUP_DATA['password1'])
        )

        # token NOVO segue válido depois do login; o link usado, não
        user = User.objects.get(email='novo@exemplo.com')
        token_fresco = activation_token_generator.make_token(user)
        self.assertTrue(activation_token_generator.check_token(user, token_fresco))
        response = self.client.get(match.group(0))
        self.assertFalse(response.context['validlink'])

    def test_login_bloqueado_ate_o_email_ser_verificado(self):
        # sem posse comprovada do e-mail, não há sessão: senão qualquer um
        # cria conta com o e-mail de outra pessoa e entra nela
        self.client.post(reverse('signup'), SIGNUP_DATA)
        response = self.client.post(
            reverse('login'),
            {'username': 'novo@exemplo.com', 'password': SIGNUP_DATA['password1']},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'não foi verificado')
        self.assertNotIn('_auth_user_id', self.client.session)

        # depois do link, o login passa
        match = re.search(r'/accounts/activate/[^/]+/[^/\s]+/', mail.outbox[0].body)
        self.client.get(match.group(0))
        response = self.client.post(
            reverse('login'),
            {'username': 'novo@exemplo.com', 'password': SIGNUP_DATA['password1']},
        )
        self.assertRedirects(response, reverse('home'))

    def test_token_invalido_nao_confirma_o_email(self):
        user = User.objects.create_user('vitima@exemplo.com', 'senha-forte-123')
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        response = self.client.get(f'/accounts/activate/{uid}/token-invalido/')

        self.assertFalse(response.context['validlink'])
        user.refresh_from_db()
        self.assertFalse(user.email_verified)
