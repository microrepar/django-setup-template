from pathlib import Path
from uuid import UUID

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase

from shared.models import BaseModel


class ObjetoDeTeste(BaseModel):
    """Modelo concreto mínimo: herda de BaseModel sem declarar id,
    timestamps ou update — só o campo próprio dele."""

    nome = models.CharField(max_length=10)

    class Meta:
        app_label = 'shared'


class TestBaseModel(TestCase):
    """O BaseModel concentra o que TODO modelo do projeto deve ter — UUID
    como pk, timestamps de criação/atualização e o helper update() — para
    que nenhum modelo declarado à mão divirja desse contrato. O User é a
    exceção deliberada: herda de AbstractUser (e-mail como USERNAME_FIELD)
    e não ganha UUID nem timestamps por cima. Padrão do projeto Imprensa.

    A tabela do ObjetoDeTeste nasce sem setup: registrado em shared (app
    sem migrations), ele é criado pelo run-syncdb que monta o banco de
    teste — migrations do projeto seguem intactas."""

    def test_base_model_e_abstrato(self):
        """Sem abstract o Django criaria uma tabela para o próprio
        BaseModel — ele é contrato, não registro"""
        self.assertTrue(BaseModel._meta.abstract)

    def test_herdeiro_nasce_com_pk_uuid_e_timestamps(self):
        """Quem herda BaseModel não declara id/created_at/updated_at: o
        contrato vem pronto, sem chance de divergência entre modelos"""
        instance = ObjetoDeTeste.objects.create(nome='abc')

        self.assertIsInstance(instance.pk, UUID)
        self.assertIsNotNone(instance.created_at)
        self.assertIsNotNone(instance.updated_at)

    def test_update_altera_e_persiste_em_uma_chamada(self):
        instance = ObjetoDeTeste.objects.create(nome='antes')

        instance.update(nome='depois')

        self.assertEqual(ObjetoDeTeste.objects.get(pk=instance.pk).nome, 'depois')

    def test_update_sem_commit_nao_persiste(self):
        instance = ObjetoDeTeste.objects.create(nome='antes')

        instance.update(commit=False, nome='depois')

        self.assertEqual(instance.nome, 'depois')
        self.assertEqual(ObjetoDeTeste.objects.get(pk=instance.pk).nome, 'antes')

    def test_todo_model_do_projeto_herde_de_base_model(self):
        """A regra "modelo novo herda de BaseModel" não pode depender de
        memória: este teste enumera os modelos concretos dos apps do
        projeto e falha no primeiro que herdar de models.Model direto —
        id UUID, timestamps e update() têm que vir do contrato único.
        App do projeto = pacote direto na raiz do repo; o .venv também
        mora dentro do repo, então "caminho sob BASE_DIR" não bastaria —
        django.contrib e axes instalados lá entrariam na somatória.
        O User é a exceção deliberada (AbstractUser, e-mail como
        USERNAME_FIELD)."""
        base_dir = Path(settings.BASE_DIR)
        user_model = get_user_model()

        violacoes = sorted(
            f'{model._meta.app_label}.{model.__name__}'
            for model in apps.get_models()
            if Path(model._meta.app_config.path).parent == base_dir
            and model is not user_model
            and not issubclass(model, BaseModel)
        )

        self.assertEqual(violacoes, [])
