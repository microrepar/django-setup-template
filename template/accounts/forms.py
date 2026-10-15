from typing import ClassVar

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm as DjangoAuthenticationForm,
)
from django.contrib.auth.forms import (
    PasswordResetForm as DjangoPasswordResetForm,
)
from django.contrib.auth.forms import (
    UserChangeForm as DjangoUserChangeForm,
)
from django.contrib.auth.forms import (
    UserCreationForm,
)
from django.template.loader import render_to_string

from shared.email_backends import quota_chain_available
from shared.tasks import send_email_task

from .models import User


class AuthenticationForm(DjangoAuthenticationForm):
    """Login exige e-mail verificado pelo link do cadastro.

    Sem isso, qualquer pessoa cria conta com o e-mail de outra e entra
    nela sem nunca ter provado posse do endereço.
    """

    error_messages: ClassVar[dict] = {
        **DjangoAuthenticationForm.error_messages,
        'invalid_login': 'E-mail ou senha inválidos.',
    }

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        # Staff/superuser passa direto: contas criadas por management command
        # (createsuperuser) nascem sem e-mail verificado e não podem ficar
        # trancadas fora do admin.
        if not user.email_verified and not user.is_staff:
            raise forms.ValidationError(
                'Seu e-mail ainda não foi verificado. Acesse o link enviado no '
                'cadastro para ativar a conta.',
                code='email_not_verified',
            )


class PasswordResetForm(DjangoPasswordResetForm):
    """E-mail de reset enfileirado no Celery — o envio não bloqueia a requisição."""

    def clean(self):
        cleaned_data = super().clean()
        # O probe da cota só importa com o formulário válido: sem isso, todo
        # submit inválido gastaria uma consulta ao Google.
        if self.errors:
            return cleaned_data
        # Gate síncrono: sem cota na fila de envio, recusa na hora — o
        # usuário não pode ver "enviamos" de um e-mail que vai morrer no
        # worker. A recusa é igual existindo ou não a conta: cota é
        # ortogonal, não vaza existência de e-mail.
        if not quota_chain_available():
            raise forms.ValidationError(
                'A capacidade diária de envios do sistema foi esgotada. '
                'Tente novamente amanhã.',
                code='quota_exhausted',
            )
        return cleaned_data

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        subject = render_to_string(subject_template_name, context)
        # uma linha única, como o formulário padrão do Django
        subject = ''.join(subject.splitlines()).strip()
        body = render_to_string(email_template_name, context)
        send_email_task.delay(subject, body, [to_email])


class UserChangeForm(DjangoUserChangeForm):
    """O padrão referencia o User do auth.models; amarramos ao nosso."""

    class Meta(DjangoUserChangeForm.Meta):
        model = User
        fields = '__all__'


class SignupForm(UserCreationForm):
    email = forms.EmailField(label='E-mail')

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')
        labels: ClassVar[dict] = {
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
        }

    def clean_email(self):
        # Normaliza antes da checagem de unicidade do ModelForm.
        return self.cleaned_data['email'].lower()

    def clean(self):
        cleaned_data = super().clean()
        # O probe da cota só importa com o formulário válido: sem isso, todo
        # submit inválido gastaria uma consulta ao Google.
        if self.errors:
            return cleaned_data
        # Gate síncrono: sem cota na fila de envio, a conta nem nasce —
        # cadastro sem e-mail de ativação é conta morta.
        if not quota_chain_available():
            raise forms.ValidationError(
                'A capacidade diária de cadastros do sistema foi esgotada. '
                'Tente novamente amanhã.',
                code='quota_exhausted',
            )
        return cleaned_data
