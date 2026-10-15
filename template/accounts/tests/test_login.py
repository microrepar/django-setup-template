from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

PASSWORD = 'senha-forte-123'


class LoginByEmailTestCase(TestCase):
    """O login é por e-mail e não diferencia maiúsculas de minúsculas."""

    def setUp(self):
        self.user = User.objects.create_user(
            'Usuario@Exemplo.com', PASSWORD, first_name='Usuário', last_name='de Teste',
            email_verified=True,
        )

    def post_login(self, email, password=PASSWORD):
        # O campo do AuthenticationForm se chama 'username' mesmo com USERNAME_FIELD=email.
        return self.client.post(reverse('login'), {'username': email, 'password': password})

    def test_login_with_registered_email_succeeds(self):
        response = self.post_login('usuario@exemplo.com')
        self.assertRedirects(response, reverse('home'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_login_is_case_insensitive(self):
        response = self.post_login('USUARIO@EXEMPLO.COM')
        self.assertRedirects(response, reverse('home'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_login_with_wrong_password_fails(self):
        response = self.post_login('usuario@exemplo.com', password='senha-errada')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'inválidos')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_failed_login_keeps_email_filled(self):
        # o erro é da senha: apagar o e-mail digitado só atrapalha quem errou
        # a senha e acerta o restante
        response = self.post_login('usuario@exemplo.com', password='senha-errada')

        self.assertContains(response, 'value="usuario@exemplo.com"')

    def test_login_with_unknown_email_fails(self):
        response = self.post_login('ninguem@exemplo.com')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'inválidos')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_staff_logs_in_without_verified_email(self):
        # contas de management command (createsuperuser) nascem sem e-mail
        # verificado e não podem ficar trancadas fora do admin
        User.objects.create_superuser('chefe@exemplo.com', PASSWORD)

        response = self.post_login('chefe@exemplo.com')

        self.assertRedirects(response, reverse('home'))

    def test_home_shows_profile_button_to_common_user(self):
        # usuário comum logado tem ação real na home (perfil), sem botão de
        # admin que ele não pode usar e sem convite a entrar de novo
        self.client.login(email='usuario@exemplo.com', password=PASSWORD)

        response = self.client.get(reverse('home'))

        self.assertContains(response, 'Meu perfil')
        self.assertNotContains(response, 'Acessar Admin')
        self.assertNotContains(response, 'Entrar no Sistema')
