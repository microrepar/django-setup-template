from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    """Usuário autenticado por e-mail (sem username)."""

    username = None
    email = models.EmailField('e-mail', unique=True)
    # Posse do e-mail comprovada pelo link de ativação do cadastro.
    email_verified = models.BooleanField('e-mail verificado', default=False)
    # Incrementado a cada verificação: entra no hash do token de ativação e
    # mata o link usado (uso único). Tokens novos nascem com o valor novo.
    activation_nonce = models.PositiveIntegerField('nonce de ativação', default=0)
    # Aceso quando o e-mail de ativação falha de vez (retries do Celery
    # esgotados — ex.: a cota da fila de envio acabou entre o gate do
    # formulário e o task, corrida que não dá para fechar). A conta existe,
    # mas o link nunca chegou: registro consultável no admin. Apagado
    # quando um reenvio passa.
    activation_email_failed = models.BooleanField('e-mail de ativação não entregue', default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS: ClassVar[list] = ['first_name', 'last_name']

    objects = UserManager()

    def save(self, *args, **kwargs):
        # Unicidade efetiva: e-mails diferem só por caixa não podem coexistir.
        self.email = (self.email or '').lower()
        super().save(*args, **kwargs)
