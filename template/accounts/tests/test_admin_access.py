from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class AdminAccessMessageTestCase(TestCase):
    """Conta comum autenticada recebe aviso claro no admin, sem convite a 'trocar de conta'.

    O template original do Django sugere 'login com uma conta diferente', sem
    oferecer botão algum — conta sem staff não ganha acesso ao admin trocando
    de conta. O aviso precisa dizer isso com honestidade e oferecer a volta
    ao site.
    """

    def test_authenticated_non_staff_sees_denial_message(self):
        user = User.objects.create_user(
            'semstaff@exemplo.com', 'senha-forte-123', email_verified=True
        )
        # force_login: o alvo do teste é a página, não a autenticação — e o
        # login via client.login não trafega request, que o axes exige
        self.client.force_login(user)

        response = self.client.get('/admin/login/?next=/admin/')

        self.assertContains(response, 'não tem permissão')
        self.assertContains(response, 'área administrativa')
        self.assertContains(response, 'semstaff@exemplo.com')
        self.assertContains(response, 'Voltar ao início')
        # o convite sem botão do template original não pode voltar
        self.assertNotContains(response, 'conta diferente')

    def test_anonymous_sees_plain_admin_login(self):
        response = self.client.get('/admin/login/?next=/admin/')

        self.assertNotContains(response, 'não tem permissão')
