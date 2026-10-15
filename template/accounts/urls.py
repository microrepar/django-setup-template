from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import TemplateView

from . import views
from .forms import PasswordResetForm

urlpatterns = [
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    # Autenticação (equivalente a django.contrib.auth.urls), com o LoginView
    # do projeto, que bloqueia e-mail não verificado.
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path(
        'password_reset/',
        auth_views.PasswordResetView.as_view(form_class=PasswordResetForm),
        name='password_reset',
    ),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path(
        'activate/sent/',
        TemplateView.as_view(template_name='registration/activation_sent.html'),
        name='activation_sent',
    ),
    path(
        'activate/<uidb64>/<token>/',
        views.ActivationView.as_view(),
        name='activation_confirm',
    ),
]
