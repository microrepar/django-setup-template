from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

User = get_user_model()


class UserManagerTestCase(TestCase):
    """Unicidade de e-mail é efetiva: diferenças de caixa não criam contas distintas."""

    def test_create_user_normalizes_email_to_lowercase(self):
        user = User.objects.create_user('Usuario@Exemplo.COM', 'senha-forte-123')
        self.assertEqual(user.email, 'usuario@exemplo.com')

    def test_create_user_requires_email(self):
        with self.assertRaisesMessage(ValueError, 'obrigatório'):
            User.objects.create_user('', 'senha-forte-123')

    def test_create_superuser_sets_staff_and_superuser_flags(self):
        user = User.objects.create_superuser('admin@exemplo.com', 'senha-forte-123')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_email_that_differs_only_by_case_cannot_coexist(self):
        User.objects.create_user('usuario@exemplo.com', 'senha-forte-123')
        with self.assertRaises(IntegrityError):
            User.objects.create_user('USUARIO@EXEMPLO.COM', 'outra-senha-456')

    def test_save_normalizes_email_without_the_manager(self):
        # ModelForms e admin salvam sem passar pelo manager; o save também normaliza.
        user = User(email='MiXeD@Exemplo.com', first_name='Ana')
        user.set_password('senha-forte-123')
        user.save()
        self.assertEqual(User.objects.get(pk=user.pk).email, 'mixed@exemplo.com')
