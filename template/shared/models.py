"""Modelos abstratos compartilhados.

Modelo novo do projeto herda de BaseModel — nunca de models.Model direto:
id UUID, created_at/updated_at e o helper update() vêm prontos. O User é a
única exceção (AbstractUser, para o auth do Django). O contrato é imposto
pelo teste shared/tests/test_models.py.
"""

from uuid import uuid4

from django.db import models


class TimeStampedModel(models.Model):
    """Modelo abstrato com timestamp de criação/atualização."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """Modelo abstrato com chave primária UUID4."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    class Meta:
        abstract = True

    def update(self, commit=True, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        if commit:
            self.save()


class ActiveModel(models.Model):
    """Modelo abstrato com flag de ativação."""

    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class BaseModel(TimeStampedModel, UUIDModel):
    """Modelo abstrato herdado por todos os modelos do projeto, exceto o User."""

    class Meta:
        # Subclasse de modelo abstrato não é abstrata por herança: sem isto,
        # o Django criaria uma tabela para o próprio BaseModel.
        abstract = True
