import os

# Tenta vencer a leitura do .env rodando antes do Django carregar os
# settings. O pytest-django, porém, pode configurar o Django ANTES de
# importar este conftest — por isso o patch do pytest_configure abaixo.
os.environ['CELERY_BROKER_URL'] = ''


def pytest_configure(config):
    # Testes executam as tarefas Celery eager (inline, sem broker): nada de
    # enfileirar no Redis do Compose — o worker consumiria e dispararia
    # e-mails reais pelo backend configurado no .env.
    from django.conf import settings

    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    from core.celery import app

    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True
