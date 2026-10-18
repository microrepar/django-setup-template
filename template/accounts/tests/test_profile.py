from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

PASSWORD = 'senha-forte-123'


class ProfilePermissionsTestCase(TestCase):
    """O perfil informa apenas o que a conta pode fazer — nunca o catálogo do sistema."""

    def profile_as(self, email, **user_kwargs):
        user = User.objects.create_user(email, PASSWORD, email_verified=True, **user_kwargs)
        # force_login: o alvo do teste é a página, não a autenticação — e o
        # login via client.login não trafega request, que o axes exige
        self.client.force_login(user)
        return self.client.get(reverse('profile'))

    def test_common_user_sees_what_the_account_can_do(self):
        response = self.profile_as('comum@exemplo.com')

        # informa o que dá para fazer com a conta, não um rótulo vazio
        self.assertContains(response, 'Com esta conta você pode')
        self.assertContains(response, 'alterar a sua própria senha')
        self.assertContains(response, 'não está disponível para esta conta')
        # estado explícito das flags da conta
        self.assertContains(response, 'Membro de equipe')
        self.assertContains(response, 'Superusuário')

    def test_staff_user_sees_admin_access(self):
        response = self.profile_as('staffer@exemplo.com', is_staff=True)

        self.assertContains(response, 'área administrativa')
        # membro de equipe Sim, superusuário Não
        self.assertContains(response, '>Sim<', 1)
        self.assertContains(response, '>Não<', 1)

    def test_superuser_sees_full_access_without_catalog(self):
        chefe = User.objects.create_superuser('chefe@exemplo.com', PASSWORD)
        # force_login: idem profile_as — autenticação não é o alvo do teste
        self.client.force_login(chefe)

        response = self.client.get(reverse('profile'))

        self.assertContains(response, 'superusuário')
        # as duas flags da conta aparecem como Sim para o superusuário
        self.assertContains(response, '>Sim<', 2)
        # superusuário tem tudo: listar o catálogo inteiro não informa nada
        self.assertNotContains(response, 'Permissões:')

    def test_group_permission_shows_group_and_verb(self):
        group = Group.objects.create(name='Editores')
        group.permissions.add(Permission.objects.get(codename='view_user'))
        user = User.objects.create_user('editor@exemplo.com', PASSWORD, email_verified=True)
        user.groups.add(group)
        # force_login: idem profile_as — autenticação não é o alvo do teste
        self.client.force_login(user)

        response = self.client.get(reverse('profile'))

        self.assertContains(response, 'Editores')
        # verbose_name do model já vem traduzido pelo Django (LANGUAGE_CODE)
        self.assertContains(response, 'Ver usuário')
