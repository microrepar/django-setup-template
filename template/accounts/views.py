from django.conf import settings
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Permission
from django.db.models import Q
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.generic import CreateView, TemplateView

from shared.tasks import send_email_task

from .forms import AuthenticationForm, SignupForm
from .models import User
from .tokens import activation_token_generator

# Codename do Django é verbo_model ("add_user"); o nome salvo em Permission
# é em inglês ("Can add user") — traduzimos o verbo para exibição.
PERMISSION_VERBS = {'add': 'Adicionar', 'change': 'Alterar', 'delete': 'Excluir', 'view': 'Ver'}


class LoginView(auth_views.LoginView):
    # AuthenticationForm do projeto: bloqueia e-mail não verificado.
    authentication_form = AuthenticationForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # O LoginView do Django injeta site_name = get_current_site(): sem
        # django.contrib.sites isso é o host da requisição (IP:porta), que
        # sobrescreve o context processor da marca — a navbar só perderia
        # o nome do site nesta página.
        context['site_name'] = settings.SITE_NAME
        return context


class SignupView(CreateView):
    template_name = 'registration/signup.html'
    form_class = SignupForm
    success_url = reverse_lazy('activation_sent')

    def form_valid(self, form):
        # Cadastra sem logar: a posse do e-mail precisa ser comprovada pelo
        # link de ativação — sem isso, qualquer um cria conta com o e-mail
        # de outra pessoa e entra nele.
        response = super().form_valid(form)
        self.send_activation_email(form.instance)
        return response

    def send_activation_email(self, user):
        context = {
            'user': user,
            'protocol': self.request.scheme,
            'domain': self.request.get_host(),
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': activation_token_generator.make_token(user),
        }
        # enfileira no Celery: a resposta do cadastro não espera o Google.
        # user_id liga o task ao usuário para registrar a falha final do
        # envio (corrida entre o gate de cota e o task).
        send_email_task.delay(
            render_to_string('registration/activation_subject.txt', context).strip(),
            render_to_string('registration/activation_email.html', context),
            [user.email],
            user_id=user.pk,
        )


class ActivationView(TemplateView):
    """Confirma a posse do e-mail pelo link do cadastro (uid + token, como o reset de senha)."""

    template_name = 'registration/activation_confirm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_user(kwargs['uidb64'])
        valid = user is not None and activation_token_generator.check_token(user, kwargs['token'])
        if valid and not user.email_verified:
            user.email_verified = True
            # incrementa o nonce: entra no hash do token e mata o link usado
            user.activation_nonce += 1
            user.save(update_fields=['email_verified', 'activation_nonce'])
        context['validlink'] = valid
        return context

    @staticmethod
    def get_user(uidb64):
        try:
            return User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return None


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """Concluir o reset também verifica o e-mail: provar a posse da caixa
    pelo link do reset equivale à prova do link de ativação — fallback
    quando esse falhou (expirou no timeout herdado do gerador, senha trocada
    antes do clique, e-mail que não chegou). A troca de senha já invalida
    tokens de ativação pendentes: a senha entra no hash (ver tokens.py).
    """

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.user
        if not user.email_verified or user.activation_email_failed:
            user.email_verified = True
            user.activation_email_failed = False
            user.save(update_fields=['email_verified', 'activation_email_failed'])
        return response


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'registration/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['groups'] = user.groups.all()
        # Permissões efetivas (próprias + herdadas de grupos). Superusuário
        # tem todas por definição — listar o catálogo inteiro não informa.
        permissions = (
            Permission.objects.filter(Q(user=user) | Q(group__user=user)).distinct()
            if not user.is_superuser
            else Permission.objects.none()
        )
        context['permissions'] = [
            f'{PERMISSION_VERBS.get(p.codename.split("_", 1)[0], p.codename)} {p.content_type.name}'
            for p in permissions
        ]
        return context
