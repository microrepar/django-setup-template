from django.conf import settings
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
        # force_login: o alvo do teste é a home, não a autenticação — e o
        # login via client.login não trafega request, que o axes exige
        self.client.force_login(self.user)

        response = self.client.get(reverse('home'))

        self.assertContains(response, 'Meu perfil')
        self.assertNotContains(response, 'Acessar Admin')
        self.assertNotContains(response, 'Entrar no Sistema')


class BruteForceLockoutTestCase(TestCase):
    """django-axes: 5 tentativas falhas do mesmo IP bloqueiam o login por
    1 hora. O bloqueio só protege de verdade se o IP contado for o real —
    por isso o X-Forwarded-For forjado (fora de TRUST_PROXY) não pode
    fabricar um "cliente novo" a cada tentativa."""

    def setUp(self):
        self.user = User.objects.create_user(
            'usuario@exemplo.com', PASSWORD, email_verified=True,
        )

    def post_login(self, password='senha-errada', **extra):
        return self.client.post(
            reverse('login'), {'username': 'usuario@exemplo.com', 'password': password}, **extra
        )

    def test_quinta_falha_bloqueia_proxima_tentativa(self):
        # antes do limite, as falhas exibem o erro normal do formulário...
        for _ in range(settings.AXES_FAILURE_LIMIT - 1):
            response = self.post_login()
            self.assertEqual(response.status_code, 200)

        # ...a tentativa que ATINGE o limite já vem bloqueada (429 com a página)
        response = self.post_login()
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, 'CONTA BLOQUEADA', status_code=429)

        # e o bloqueio persiste na seguinte, MESMO com a senha correta
        response = self.post_login(password=PASSWORD)

        self.assertEqual(response.status_code, 429)

    def test_xff_forjado_nao_desvia_o_bloqueio(self):
        # atacante renovando o X-Forwarded-For a cada tentativa: sem
        # TRUST_PROXY o IP contado é o REMOTE_ADDR, então o bloqueio cai
        # mesmo assim — é a razão de existir da fonte única de IP
        for i in range(settings.AXES_FAILURE_LIMIT):
            self.post_login(HTTP_X_FORWARDED_FOR=f'10.0.0.{i}')

        response = self.post_login(password=PASSWORD)

        self.assertEqual(response.status_code, 429)
