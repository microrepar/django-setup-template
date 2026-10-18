# Guia de Configuração do Projeto Django com Docker e Docker Compose

Guia completo para configurar um projeto Django com modelo de Usuário customizado, gerenciamento de dependências com uv, infraestrutura Docker, Tailwind CSS v4 e HTMX.

**Este documento é a especificação.** Cada arquivo aparece **uma única vez**, já em seu estado final, e existe **um único runbook de execução** (seção [EXECUÇÃO OBRIGATÓRIA](#execução-obrigatória-do-projeto)).

## Índice

1. [Regras para o Agente](#regras-para-o-agente)
2. [Pré-requisitos](#pré-requisitos)
3. [Seleção da Versão do Django](#seleção-da-versão-do-django)
4. [Pré-requisitos do Projeto](#pré-requisitos-do-projeto)
5. [Configuração do Projeto Django](#configuração-do-projeto-django)
6. [Configuração do Ambiente](#configuração-do-ambiente)
7. [Modelo de Usuário Customizado](#modelo-de-usuário-customizado)
8. [Infraestrutura Docker](#infraestrutura-docker)
9. [Tailwind CSS v4 Standalone, HTMX e Templates](#tailwind-css-v4-standalone-htmx-e-templates)
10. [EXECUÇÃO OBRIGATÓRIA DO PROJETO](#execução-obrigatória-do-projeto)
11. [Notas Importantes](#notas-importantes)
12. [Fluxo Obrigatório: Adicionar Dependências Python](#fluxo-obrigatório-adicionar-dependências-python)
13. [Solução de Problemas](#solução-de-problemas)
14. [Referências](#referências)

---

## Regras para o Agente

Estas regras se aplicam a quem executa este guia (agente de IA ou pessoa), inclusive quando o objetivo é criar um PRD (Product Requirements Document).

### Regra 1: EXECUÇÃO LITERAL

- **NÃO modifique** qualquer configuração especificada neste guia
- **NÃO improvise** "melhorias" ou "adaptações"
- **NÃO substitua** tecnologias, comandos, paths ou estruturas
- Se o guia diz X, você faz X. Se você acha que X está "errado", você AINDA faz X

### Regra 2: PROIBIÇÕES EXPLÍCITAS

É **ESTRITAMENTE PROIBIDO**:

❌ **NÃO** substituir bind mounts por volumes nomeados Docker
❌ **NÃO** substituir arquivos de configuração separados (`nginx.conf`) por comandos inline
❌ **NÃO** substituir `env_file: .env` por variáveis de ambiente inline
❌ **NÃO** alterar paths especificados (ex: `core/static/core/js/htmx/`)
❌ **NÃO** usar raciocínio para "corrigir" supostos problemas de compatibilidade
❌ **NÃO** adicionar notas sobre "WSL2 incompatível" ou qualquer justificativa para mudar o guia
❌ **NÃO** criar scripts *wrapper* para o Docker Compose (ex.: `docker-compose-dev.sh`); execute `docker compose <comando>` diretamente

### Regra 3: EXEMPLOS DE VIOLAÇÕES

**O que o guia especifica:**

```yaml
volumes:
  - ./staticfiles:/code/staticfiles
```

**VIOLAÇÃO** (o que NÃO fazer):

```yaml
volumes:
  - staticfiles:/code/staticfiles  # ❌ Volume nomeado NÃO é bind mount
```

**O que o guia especifica:**

```yaml
env_file: .env
```

**VIOLAÇÃO** (o que NÃO fazer):

```yaml
environment:
  - SECRET_KEY=value  # ❌ Variáveis inline NÃO substituem env_file
```

### Regra 4: CHECKLIST DE VALIDAÇÃO

Ao executar este guia, verifique que:

- [ ] Todo path de arquivo foi copiado EXATAMENTE como está no guia
- [ ] Todo comando foi copiado EXATAMENTE como está no guia
- [ ] Todo conteúdo de arquivo YAML/Python/HTML/TOML foi copiado EXATAMENTE
- [ ] Nenhuma "melhoria" ou "adaptação" foi adicionada
- [ ] Nenhuma justificativa do tipo "para compatibilidade com X" foi adicionada

### Regra 5: O GUIA É A ESPECIFICAÇÃO

**Este guia é a especificação, não uma sugestão.**

Se você tem dúvida sobre como implementar algo, a resposta está **neste guia**.

### Regra 6: LACUNAS SÃO DEFEITO DO GUIA

Este guia foi escrito para ser **completo**: todos os arquivos, comandos, valores e paths necessários estão especificados.

Se você encontrar algo que **não** está especificado:

1. **PARE** a execução no ponto da lacuna
2. **Reporte** exatamente o que falta (arquivo, comando, valor ou decisão)
3. **NÃO invente** nada por conta própria; prossiga apenas com autorização explícita do usuário

Interpretar, adivinhar ou "resolver com conhecimento próprio" uma lacuna **não** é permitido — é justamente o que produz divergência entre execuções.

### Regra 7: OS CONTROLES DE SEGURANÇA SÃO PARTE DA ESPECIFICAÇÃO

Os controles abaixo **NÃO PODEM** ser removidos, afrouxados ou "simplificados", mesmo que atrapalhem a execução ou pareçam burocráticos:

❌ **NÃO** criar senha fixa/documentada para nenhum usuário (nem para o superusuário de desenvolvimento)
❌ **NÃO** reintroduzir valor default utilizável em `SECRET_KEY`, `DB_PASS` ou `REDIS_PASSWORD`
❌ **NÃO** usar `ALLOWED_HOSTS='*'` nem `DEBUG=True` como default de produção
❌ **NÃO** publicar portas em `0.0.0.0` — **exceção única**: a porta canônica do Nginx (`8080:80`), publicada em todas as interfaces por decisão explícita do projeto; `5432` e `8000` permanecem em `127.0.0.1`
❌ **NÃO** remover o rate limiting de `/accounts/login/`, `/accounts/password_reset/` e `/admin/login/`
❌ **NÃO** remover a validação de integridade (sha256) do binário do Tailwind
❌ **NÃO** servir `/media/` publicamente (o location é `internal` por padrão)
❌ **NÃO** remover as validações de startup de `settings.py` (elas existem para transformar configuração insegura em falha explícita)

Se algum destes controles impedir a execução, trate como **defeito do guia** e siga a Regra 6 (pare e reporte).

---

## Pré-requisitos

As ferramentas a seguir devem estar **pré-instaladas pelo usuário na máquina host** antes de iniciar esta configuração:

- **uv** - Gerenciador de dependências Python (instalação via curl ou pip)
- **Docker Desktop** - Para executar containers
- **Git** - Controle de versão
- **ignr** - Gerenciador de arquivos ignorados

**⚠️IMPORTANTE** - este guia de configuração assume que todos os pré-requisitos acima já estão disponíveis no ambiente de desenvolvimento.

### Verificar as instalações

```bash
uv --version
docker --version
git --version
uv tool list
```

### Verificação do ignr

**Nota**: O `ignr` não suporta `--version`. Verifique com:

```bash
uv run ignr -h  # ou simplesmente: ignr --help
```

O guia usa `ignr -n django` (`--new`), que **grava** o arquivo `.gitignore` no diretório atual. A variante `-p django` (`--preview`) apenas **imprime** o conteúdo e exigiria redirecionamento — não é usada aqui.

### Versões usadas por este guia

| Ferramenta | Versão | Observação |
|---|---|---|
| Python | **3.13** | ambiente virtual (`uv venv 3.13`) e imagem Docker (`python:3.13-slim`) |
| Django | **5.2.x** (LTS, padrão) | `Requires-Python: >=3.10` (PyPI) |
| PostgreSQL | 15 | imagem `postgres:15` |
| Redis | 6.2 | imagem `redis:6.2` |
| HTMX | 2.0.9 | download via CDN na seção 9 |
| Tailwind CSS | 4.1.18 | CLI standalone, baixado no build da imagem |

**Imagens e binários fixados por integridade** (mitiga "tag mutável" e supply chain):

| Artefato | Referência fixada | Verificação |
|---|---|---|
| PostgreSQL | `postgres:15@sha256:f189cf3e8ad81c21e70c78735f18c65cf1a2635fe5aa2bb59220dda334ee26a9` | digest no `docker-compose.yml` |
| Redis | `redis:6.2@sha256:a54ecc83b70d33cf1c1d89f0301ba39b6753b91184bfd9a1cb4ef1f805fefc2d` | digest no `docker-compose.yml` |
| Nginx | `nginx:1.31.0@sha256:06aa3d7be10bc6307990c81bdca075793132e9163391abc370c015e344e23128` | versão + digest no `docker-compose.yml` |
| Tailwind CLI (linux-x64) | `v4.1.18` — `sha256:737becf8d4ad1115ea98df69fa94026d402ca8feb91306a035b5b004167da8dd` | `sha256sum -c` no `Dockerfile` |

⚠️ **Atualizar uma versão** exige atualizar a referência **e** o digest/hash correspondente no mesmo commit — nunca remover a verificação para "fazer o build passar".

---

## Seleção da Versão do Django

⚠️ **INSTRUÇÃO DO AGENTE DE IA**: No início da execução, se já não tiver sido informado, pergunte ao usuário qual versão do Django ele deseja para o projeto, de preferência a versão LTS (Suporte de Longo Prazo).

### Versões Django Suportadas e Compatibilidade com Python

Compatibilidade verificada na API do PyPI. Todas as versões Python exigidas são atendidas pelo Python 3.13 deste guia.

| Versão Django | Python exigido (`Requires-Python`) | Status de Suporte |
|---------------|-----------------------------------|-------------------|
| **Django 5.2.x** | >=3.10 | ✅ **LTS** (padrão deste guia) |
| **Django 6.1.x** | >=3.12 | ✅ Estável (recursos mais recentes) |

Versões anteriores ficam **fora** deste guia: a série 5.0.x não é LTS e a série 4.2.x está fora de suporte desde abril/2026.

### Prompt de Seleção

Pergunte ao usuário se ele ainda não selecionou uma versão:

```plain
Qual versão do Django você gostaria de usar para este projeto?
1. Django 5.2.x (LTS, recomendado)
2. Django 6.1.x (estável, requer Python >= 3.12)

Por favor, entre com sua escolha (1 ou 2):
```

### Comandos de Instalação por Escolha

Use **exatamente** o comando correspondente à escolha, na seção [Configuração do Projeto Django](#configuração-do-projeto-django):

| Escolha | Comando |
|---|---|
| Django 5.2.x (padrão) | `uv add "Django>=5.2,<6.0"` |
| Django 6.1.x | `uv add "Django>=6.1,<7.0"` |

**Este guia é validado com Django 5.2.x.** A escolha por Django 6.1.x não é validada aqui: siga os mesmos comandos, mas verifique o resultado de cada fase.

Se nenhuma versão for escolhida, use **Django 5.2.x** (comando `uv add "Django>=5.2,<6.0"`).

---

## Pré-requisitos do Projeto

⚠️ **IMPORTANTE**: todas as etapas desta seção devem ser concluídas a partir do **diretório raiz do projeto**.

### Regra de substituição de `[nome_do_projeto]`

Em todo este guia, o token **`[nome_do_projeto]`** deve ser substituído pelo **basename do diretório raiz do projeto** (`basename "$(pwd)"`), **literalmente, sem nenhuma transformação** — hífens e maiúsculas são preservados.

Exemplo: no diretório `/home/user/projetos/compare-ai`, o token vira `compare-ai`, e o nome de rede `[nome_do_projeto]_network` vira `compare-ai_network`.

### 1. Descobrir o Nome do Projeto

```bash
pwd
basename "$(pwd)"
```

O resultado de `basename "$(pwd)"` é o valor de `[nome_do_projeto]`.

⚠️ **PRECONDIÇÃO**: este guia assume que o diretório raiz **é um repositório git** — a seção [Configuração do Ambiente](#configuração-do-ambiente) usa `git add`/`git rm --cached` e a [FASE 4](#fase-4-versionamento---commit-inicial) cria o commit inicial. Se ainda não for:

```bash
git rev-parse --is-inside-work-tree 2>/dev/null || git init
```

### 2. Criar Ambiente Virtual com uv

```bash
uv init --python 3.13
uv venv
```

**Nota**: `uv init` cria `pyproject.toml`, `.python-version`, `README.md`, `.gitignore` e um `main.py` de exemplo. O `main.py` **não é usado** por este projeto e deve ser removido:

```bash
rm -f main.py
```

O `README.md` **deve ser mantido** (é referenciado por `readme = "README.md"` no `pyproject.toml`). O `.gitignore` gerado pelo `uv init` será **substituído** no passo 3.

### 3. Criar o arquivo .gitignore

```bash
uv run ignr -n django
```

### 4. Adicionar ao final do .gitignore

```bash
printf '\nstaticfiles/\ndata/\nnode_modules/\ncore/static/core/css/output.css\n.superuser-password\n' >> .gitignore
grep -q "^\.env$" .gitignore || echo ".env" >> .gitignore
```

Conteúdo adicionado ao final do `.gitignore`:

```.gitignore
staticfiles/
data/
node_modules/
core/static/core/css/output.css
.superuser-password
.env
.claude/
```

**Nota**: o template `django` do `ignr` já inclui `.env`; o comando acima é **idempotente** (só acrescenta a regra se ela faltar). `.superuser-password` é o arquivo temporário com a senha gerada do superusuário ([FASE 2](#fase-2-execução)): ele **nunca** deve ser versionado e deve ser apagado após a senha ser guardada em um gerenciador de segredos. `core/static/core/css/output.css` é artefato gerado pelo build do Tailwind CSS (seção 9) e **não** deve ser versionado. `staticfiles/` é o diretório do `collectstatic` e `data/` guarda os dados do PostgreSQL do container.

### 5. Adicionar a configuração ./.vscode/settings.json

```bash
mkdir -p .vscode
```

Crie o arquivo `./.vscode/settings.json`:

```json
{
    "material-icon-theme.folders.associations": {
        "core": "rules",
        "adapters": "pipe",
        "external": "tools",
        "pages": "rules",
        "user": "lib",
        "notebook": "lib",
        "pagesection": "lib",
        "sentencelabel": "lib",
        "sentencetranslation": "lib",
        "alembic": "config",
        ".streamlit": "config",
        ".documentation": "resource",
        "persistence": "database",
        "app_pages": "app"
    },
    "files.exclude": {
        "**/*.pyc": {"when": "$(basename).py"},
        "**/__pycache__": true,
        "**/*.pytest_cache": true
    }
}
```

---

## Configuração do Projeto Django

### 1. Instalar o Django e Dependências

```bash
uv cache clean
uv add "Django>=5.2,<6.0" psycopg2-binary python-dotenv django-htmx
```

⚠️ O comando acima instala o **Django 5.2.x** (padrão). Para Django 6.1.x, troque a primeira dependência pelo comando da [tabela de escolhas](#comandos-de-instalação-por-escolha).

**Nota sobre `django-extensions`**: ele **não** é mais dependência de runtime. É uma ferramenta de desenvolvimento (traz `shell_plus`, `runserver_plus` com debugger Werkzeug, `sqldsn`) e, se instalada na imagem, amplia a superfície de ataque do container. Fica no grupo `dev` e **fora** do `INSTALLED_APPS`, disponível para comandos executados **no host** (`uv run python manage.py shell_plus`).

### 2. Instalar Dependências de Desenvolvimento

```bash
uv add --dev pytest pytest-cov pytest-django taskipy ruff django-extensions
```

### 3. Adicionar Dependências do Celery

```bash
uv add celery redis
```

### 4. Instalar Dependências no Ambiente Virtual

```bash
uv sync
```

### 5. Ajustar a Restrição de Versão do Python

Edite `pyproject.toml` e garanta a chave `requires-python` exatamente assim:

```toml
[project]
# ...
requires-python = ">=3.13,<4.0"
```

**Nota**: o limite inferior é a versão 3.13 porque é a versão usada tanto no ambiente virtual quanto na imagem Docker (`python:3.13-slim`). O limite superior `<4.0` acompanha o `Requires-Python` das ferramentas de desenvolvimento (`taskipy` declara `>=3.6,<4.0`).

### 6. Criar Projeto Django

```bash
uv run django-admin startproject core .
```

O comando cria o pacote `core/` na raiz (com `settings.py`, `urls.py`, `wsgi.py`, `asgi.py`) e o `manage.py`. O `settings.py` gerado será **substituído integralmente** na seção [Modelo de Usuário Customizado](#modelo-de-usuário-customizado).

---

## Configuração do Ambiente

### 1. Criar Arquivo .env.example

⚠️ **CRÍTICO**: O arquivo `.env` **NUNCA** deve ser commitado no git. Use sempre `.env.example` como template.

Crie `.env.example` na raiz do projeto:

```.env
# Django Settings
# ATENÇÃO: este arquivo NÃO contém nenhum segredo utilizável. SECRET_KEY, DB_PASS,
# REDIS_PASSWORD e CELERY_BROKER_URL são gerados no passo 2 desta seção.
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS='localhost,127.0.0.1'
CSRF_TRUSTED_ORIGINS='http://localhost:8080,http://localhost:8000,http://127.0.0.1:8080,http://127.0.0.1:8000'

# Banco de dados
DB_ENGINE=postgresql
DB_USERNAME=postgres
DB_PASS=
DB_HOST=db
DB_PORT=5432
DB_NAME=postgres

# Redis / Celery
REDIS_PASSWORD=
CELERY_BROKER_URL=

# Segurança de transporte e cookies (ver "Endurecimento de segurança" nas Notas Importantes)
# Desenvolvimento local sobre HTTP: mantenha False/0.
# Produção sobre HTTPS: SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True,
# SECURE_SSL_REDIRECT=True e SECURE_HSTS_SECONDS=31536000 — o startup EXIGE as três primeiras.
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_SSL_REDIRECT=False
SECURE_HSTS_SECONDS=0
```

**Sobre as variáveis de banco**: com `DB_ENGINE=postgresql`, o Django (inclusive rodando no host, via `uv run`) conecta no PostgreSQL. No container `web`, `DB_HOST=db` aponta para o serviço `db` da rede Docker. Para acessar o banco **do host**, use `DB_HOST=localhost` (a porta `5432` é publicada **apenas em `127.0.0.1`** no `docker-compose.yml`), por exemplo:

```bash
DB_HOST=localhost uv run python manage.py migrate
```

### 2. Criar e preencher o .env local

```bash
cp .env.example .env
```

O `.env` é o arquivo lido pelo `env_file: .env` do Docker Compose **e** pelo `python-dotenv` do `settings.py`.

⚠️ **CRÍTICO**: sem o arquivo `.env`, **nenhum** comando do Docker Compose funciona (`env file .env not found`).

⚠️ **CRÍTICO — SEM SEGREDO DEFAULT**: gere `SECRET_KEY`, `DB_PASS` e `REDIS_PASSWORD` **agora**, com valores únicos desta máquina. Nenhum valor aparece na tela: o script grava direto no `.env` e valida que cada chave ficou preenchida.

```bash
uv run python - <<'PY'
import pathlib
import secrets

from django.core.management.utils import get_random_secret_key

env = pathlib.Path('.env')
redis_senha = secrets.token_urlsafe(32)

valores = {
    'SECRET_KEY': f"'{get_random_secret_key()}'",
    'DB_PASS': f"'{secrets.token_urlsafe(32)}'",
    'REDIS_PASSWORD': f"'{redis_senha}'",
    'CELERY_BROKER_URL': f"redis://:{redis_senha}@redis:6379/0",
}

linhas = []
for linha in env.read_text().splitlines():
    chave = linha.split('=', 1)[0] if '=' in linha else None
    linhas.append(f"{chave}={valores[chave]}" if chave in valores else linha)

env.write_text('\n'.join(linhas) + '\n')

for chave in valores:
    assert any(l.startswith(f'{chave}=') and len(l.split('=', 1)[1].strip().strip("'")) >= 20 for l in linhas), chave

print('SECRET_KEY, DB_PASS e REDIS_PASSWORD gerados e gravados em .env (valores não exibidos)')
PY

# Restringir a leitura do .env ao dono do arquivo
chmod 600 .env
```

**Notas**:

- Windows (PowerShell) não tem `chmod`; use: `icacls .env /inheritance:r /grant:r "$env:USERNAME:R"`.
- Os três segredos são **únicos por máquina** e vivem apenas no `.env` (que é ignorado pelo git) — nunca no `.env.example`, nunca no repositório, nunca em documentação.
- `CELERY_BROKER_URL` embute `REDIS_PASSWORD`; o serviço `redis` do Compose sobe com `--requirepass ${REDIS_PASSWORD}`.

### 3. Atualizar .gitignore

```bash
# Verificar se .env está no gitignore
grep -q "^\.env$" .gitignore || echo ".env" >> .gitignore

# Remover .env do versionamento se foi adicionado acidentalmente
git rm --cached .env 2>/dev/null || true

# Adicionar .env.example ao versionamento
git add .env.example
```

---

## Modelo de Usuário Customizado

Esta seção cria o app `accounts`, o modelo de usuário customizado, os modelos base reutilizáveis e o `core/settings.py` completo.

### 1. Criar a Aplicação Accounts

```bash
uv run python manage.py startapp accounts
```

### 2. Criar Modelo de Usuário Customizado

Edite `accounts/models.py`:

```python
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    pass
```

### 3. Registrar Usuário no Admin

Edite `accounts/admin.py`:

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    pass
```

### 4. Criar Modelos Base (Base Models)

Crie o módulo `core/base_models/` com classes base reutilizáveis para todos os modelos do projeto.

#### 4.1 Criar o Diretório

```bash
mkdir -p core/base_models
touch core/base_models/__init__.py
```

#### 4.2 Criar Mixins Base (`core/base_models/mixins.py`)

```python
from django.db import models


class TimestampMixin(models.Model):
    """Adiciona campos de timestamp (created_at, updated_at) aos modelos."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """Permite soft delete nos modelos."""
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()
```

**Nota**: o `SoftDeleteMixin` é **opt-in**: o `BaseModel` **não** o inclui por padrão. Quando um modelo precisar de soft delete, herde explicitamente dele — ex.: `class MeuModelo(SoftDeleteMixin, BaseModel)`.

#### 4.3 Criar Modelo Base (`core/base_models/models.py`)

```python
from uuid import uuid4
from django.db import models
from .mixins import TimestampMixin


class BaseModel(TimestampMixin, models.Model):
    """Modelo base abstrato com timestamp de criação/atualização."""
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    class Meta:
        abstract = True

    def update(self, commit=True, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        if commit:
            self.save()

    @staticmethod
    def get_columns():
        return []
```

#### 4.4 Atualizar `core/base_models/__init__.py`

```python
from .mixins import TimestampMixin, SoftDeleteMixin
from .models import BaseModel

__all__ = ['TimestampMixin', 'SoftDeleteMixin', 'BaseModel']
```

#### 4.5 Estrutura Final

```
core/
└── base_models/
    ├── __init__.py
    ├── mixins.py
    └── models.py
```

### 5. Substituir `core/settings.py` por Completo

⚠️ **CRÍTICO**: substitua **todo** o conteúdo de `core/settings.py` pelo bloco abaixo. Ele já contém as leituras do `.env`, o app `accounts`, o modelo de usuário customizado, a internacionalização, os arquivos estáticos/mídia, a configuração do Celery, o middleware do HTMX e o banco dinâmico (`DB_ENGINE=postgresql` → PostgreSQL; qualquer outro valor → SQLite local).

```python
"""
Django settings for core project.

Generated by 'django-admin startproject' using Django 5.2.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

import ipaddress
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY: a chave vem do ambiente e NAO tem fallback. Ausencia de segredo e erro de
# configuracao, nao motivo para subir com um valor publico.
SECRET_KEY = os.environ.get('SECRET_KEY', '').strip()

if not SECRET_KEY or SECRET_KEY.startswith('django-insecure-') or SECRET_KEY.startswith('your-secret-key'):
    raise ImproperlyConfigured(
        "SECRET_KEY ausente ou insegura. Gere uma chave com "
        "'uv run python -c \"from django.core.management.utils import get_random_secret_key as g; print(g())\"' "
        "e grave em SECRET_KEY no .env (ver secao Configuracao do Ambiente)."
    )

# SECURITY: default seguro. DEBUG ligado exige hosts locais ou IPs de rede
# privada/VPN (validado abaixo).
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = [
    host.strip() for host in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if host.strip()
]

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS vazio. Liste os hosts explicitamente.")

if '*' in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS nao pode conter '*'. Liste os hosts explicitamente (ex.: localhost,127.0.0.1,seu-dominio)."
    )

LOCAL_HOSTS = {'localhost', '127.0.0.1', '[::1]', '::1', '0.0.0.0', 'web'}

# Redes privadas/VPN aceitas com DEBUG=True: nao sao roteaveis na internet,
# entao o dev continua sem exposicao publica (Tailscale usa a faixa CGNAT).
DEBUG_ALLOWED_NETWORKS = (
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('100.64.0.0/10'),  # CGNAT: Tailscale e afins
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fe80::/10'),
)


def _host_permitido_em_debug(host):
    """Host local (nome) ou IP literal dentro das redes privadas permitidas."""
    if host in LOCAL_HOSTS:
        return True
    try:
        ip = ipaddress.ip_address(host.strip('[]'))
    except ValueError:
        return False
    return any(ip in rede for rede in DEBUG_ALLOWED_NETWORKS)


if DEBUG and not all(_host_permitido_em_debug(host) for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured(
        "DEBUG=True so e permitido com hosts locais ou IPs de rede privada/VPN "
        "(ex.: faixa do Tailscale). Hosts atuais: "
        f"{ALLOWED_HOSTS}. Use DEBUG=False para qualquer host publico."
    )

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]

if any(not origin.startswith(('http://', 'https://')) for origin in CSRF_TRUSTED_ORIGINS):
    raise ImproperlyConfigured(
        "CSRF_TRUSTED_ORIGINS exige o esquema (http:// ou https://) em cada origem."
    )

# SECURITY: transporte e cookies por ambiente. Em producao (DEBUG=False) as flags
# abaixo sao OBRIGATORIAS - o startup falha se estiverem desligadas.
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False') == 'True'
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False') == 'True'
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0

# True por padrao no Django; explicitado para nao depender de default implicito.
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True  # o token chega ao HTMX via hx-headers no template (base.html)
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG and not (SESSION_COOKIE_SECURE and CSRF_COOKIE_SECURE and SECURE_SSL_REDIRECT):
    raise ImproperlyConfigured(
        "Com DEBUG=False e obrigatorio definir SESSION_COOKIE_SECURE=True, "
        "CSRF_COOKIE_SECURE=True e SECURE_SSL_REDIRECT=True no .env (servico atras de HTTPS). "
        "Ajuste tambem SECURE_HSTS_SECONDS (ex.: 31536000) depois de validar o dominio."
    )


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_htmx',
    'accounts',
]

AUTH_USER_MODEL = 'accounts.User'

# Login/Logout redirects
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

if os.getenv('DB_ENGINE') == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USERNAME'),
            'PASSWORD': os.getenv('DB_PASS'),
            'HOST': os.getenv('DB_HOST'),
            'PORT': os.getenv('DB_PORT'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'core' / 'static',
]

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Celery
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

**Notas sobre o bloco acima**:

- `load_dotenv(BASE_DIR / '.env')`: permite que comandos executados **no host** (`uv run python manage.py ...`) leiam o mesmo `.env` usado pelo Docker Compose. Dentro do container, as variáveis já vêm do `env_file: .env`.
- `django_htmx.middleware.HtmxMiddleware`: habilita `request.htmx` nas views. O `{% django_htmx_script %}` funciona independentemente deste middleware.
- `STATICFILES_DIRS`: **obrigatório** para que o `collectstatic` encontre `core/static/` (o pacote `core` é o projeto, não um app registrado). Sem ele, o Nginx devolve HTTP 404 para `output.css` e `htmx.min.js`.
- `TEMPLATES['DIRS']`: aponta para o diretório `templates/` da raiz.

---

## Infraestrutura Docker

### 1. Criar os Diretórios Montados pelo Docker

Os bind mounts do `docker-compose.yml` apontam para diretórios do host. Crie-os antes de subir os containers:

```bash
mkdir -p data media staticfiles staticfiles/errors
```

### 2. Criar Dockerfile

Crie `Dockerfile` na raiz do projeto:

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.13-slim

# Variáveis de ambiente para otimizar o comportamento do Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Definir locale
ENV LANG=pt_BR.UTF-8
ENV LANGUAGE=pt_BR:pt
ENV LC_ALL=pt_BR.UTF-8

# Atualiza pacotes do sistema e instala o cliente do PostgreSQL e curl
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Baixar Tailwind CSS CLI v4 para Linux e VERIFICAR a integridade (sha256 pinado)
RUN curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/download/v4.1.18/tailwindcss-linux-x64 && \
    echo "737becf8d4ad1115ea98df69fa94026d402ca8feb91306a035b5b004167da8dd  tailwindcss-linux-x64" | sha256sum -c - && \
    mv tailwindcss-linux-x64 /usr/local/bin/tailwindcss && \
    chmod +x /usr/local/bin/tailwindcss

# Definir diretório de trabalho
WORKDIR /code

# Copiar e instalar dependências do projeto
COPY requirements.txt /code/
RUN pip install -U pip
RUN pip install -r requirements.txt

# Copiar o resto do código da aplicação
COPY . /code/

# Build Tailwind CSS no container
RUN tailwindcss -i /code/core/static/core/css/input.css -o /code/core/static/core/css/output.css --minify
```

⚠️ **IMPORTANTE**: Para versões diferentes do Tailwind CSS, substitua `v4.1.18` **e** o `sha256` correspondente. Para obter o hash oficial: `curl -sLO <url> && sha256sum <arquivo>`. Nunca remova a linha do `sha256sum -c -` para "fazer o build passar".

⚠️ **IMPORTANTE**: o export do `requirements.txt` é feito **com** `--no-hashes` (passo 6 desta seção): o arquivo não contém hashes e o `pip install` do `Dockerfile` **não** usa `--require-hashes`.

**Notas sobre o Dockerfile**:

- O **CLI do Tailwind CSS instalado em `/usr/local/bin/tailwindcss` é obrigatório**: as tasks `css-build`, `css-dev` e `css-watch` (seção 9) executam exatamente esse binário via `docker compose exec web tailwindcss ...`.
- O `RUN tailwindcss ...` final compila o CSS **dentro da imagem**. Em desenvolvimento, o bind mount `.:/code` do serviço `web` **sombreia** esse arquivo: quem alimenta o `collectstatic` é o `core/static/core/css/output.css` do **host**, gerado por `uv run task css-build`. O `RUN` existe para uso da imagem **sem** o bind mount (build de produção).
- `requirements.txt` **precisa existir antes do build** (ver passo 6 desta seção).

### 3. Criar .dockerignore

Crie `.dockerignore` na raiz do projeto:

```dockerignore
# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/

# Git
.git/
.gitignore

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so

# Django
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Docker
docker-compose*.yml
Dockerfile*
.docker/
nginx.Dockerfile

# Documentation
README.md
*.md

# Data
data/
media/
staticfiles/

# Testing
.pytest_cache/
.coverage
htmlcov/

# Node
node_modules/

# Tailwind CSS
bin/tailwindcss.exe
bin/tailwindcss-macos*
bin/tailwindcss-linux*

# Scripts
scripts/*.bat
```

### 4. Criar docker-compose.yml

Crie `docker-compose.yml` na raiz do projeto, substituindo `[nome_do_projeto]` pelo basename do diretório raiz ([regra de substituição](#regra-de-substituição-de-nome_do_projeto)):

```yaml
services:
  db:
    # digest fixado: a imagem nao muda sem uma alteracao explicita neste arquivo
    image: postgres:15@sha256:f189cf3e8ad81c21e70c78735f18c65cf1a2635fe5aa2bb59220dda334ee26a9
    stdin_open: true
    tty: true
    restart: always
    volumes:
      - ./data/db:/var/lib/postgresql/data
    env_file: .env
    environment:
      - POSTGRES_USER=${DB_USERNAME}
      - POSTGRES_PASSWORD=${DB_PASS}
      - POSTGRES_DB=${DB_NAME}
    ports:
      # apenas loopback: o banco nao fica exposto na rede. O container `web` fala com ele
      # pela rede interna do Compose (DB_HOST=db).
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USERNAME} -d ${DB_NAME}"]
      interval: 5s
      timeout: 10s
      retries: 20
    networks:
      - [nome_do_projeto]_network

  web:
    platform: linux/x86_64
    build: .
    stdin_open: true
    tty: true
    restart: always
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/code
    ports:
      # apenas loopback: acesso direto ao Django para depuracao local (o caminho canonico e o Nginx em :8080)
      - "127.0.0.1:8000:8000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    networks:
      - [nome_do_projeto]_network

  nginx:
    image: nginx:1.31.0@sha256:06aa3d7be10bc6307990c81bdca075793132e9163391abc370c015e344e23128
    restart: always
    ports:
      # porta canonica de acesso, publicada em todas as interfaces
      # (acessivel pela rede; db e web permanecem apenas em loopback)
      - "8080:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./staticfiles:/code/staticfiles
      - ./media:/code/media
      - ./staticfiles/errors:/etc/nginx/errors
    depends_on:
      - web
    networks:
      - [nome_do_projeto]_network

  redis:
    image: redis:6.2@sha256:a54ecc83b70d33cf1c1d89f0301ba39b6753b91184bfd9a1cb4ef1f805fefc2d
    restart: always
    # broker protegido por senha (REDIS_PASSWORD gerado no .env), mesmo sem porta publicada
    command: redis-server --requirepass ${REDIS_PASSWORD}
    networks:
      - [nome_do_projeto]_network

  worker:
    build: .
    restart: always
    command: celery -A core worker --loglevel=info
    volumes:
      - .:/code
      - ./media:/code/media
    env_file: .env
    depends_on:
      - db
      - redis
    networks:
      - [nome_do_projeto]_network
    deploy:
      resources:
        limits:
          cpus: '2.00'
          memory: 2048M
        reservations:
          cpus: '1.00'
          memory: 1024M

networks:
  [nome_do_projeto]_network:
    driver: bridge
```

**Notas sobre o compose**:

- `env_file: .env` é a **única** fonte de variáveis de ambiente das aplicações (Regra 2). O Compose também usa esse mesmo `.env` para interpolar `${DB_NAME}`, `${DB_USERNAME}` e `${DB_PASS}` no serviço `db`.
- **Sem o arquivo `.env` o Compose aborta** com `env file .env not found`; com o bloco `DB_*` ausente/comentado, o serviço `db` falha com `Database is uninitialized and superuser password is not specified`. Por isso o passo [Criar o .env local](#2-criar-e-preencher-o-env-local) é obrigatório antes de qualquer `docker compose`.
- `./staticfiles/errors` é montado em `/etc/nginx/errors` para as páginas de erro do Nginx: os HTML criados em `core/static/errors/` (seção 5) chegam lá pelo `collectstatic` da FASE 2; o `location /errors/` do `nginx.conf` é `internal`, então as páginas não são acessíveis diretamente pela URL.
- **Portas**: `5432` e `8000` publicadas apenas em `127.0.0.1`; a porta canônica do Nginx (`8080`) é publicada em todas as interfaces (acesso pela rede). O acesso entre containers acontece pela rede interna (`web:8000`, `db:5432`, `redis:6379`), então nada disso depende da porta publicada no host.
- **Imagens por digest**: `postgres`, `redis` e `nginx` estão fixados por digest sha256. Trocar a versão exige atualizar tag **e** digest de forma consciente.
- **Redis com senha**: `${REDIS_PASSWORD}` vem do `.env`; o `CELERY_BROKER_URL` gerado no passo 2 já inclui essa senha.
- ⚠️ **`runserver` é servidor de desenvolvimento** (sem hardening, single-thread, auto-reload). Para produção, troque o `command` do serviço `web` por um servidor de aplicação atrás do nginx, por exemplo: `gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3`.

### 5. Criar Configuração do Nginx

Crie `nginx.conf` na raiz do projeto:

```nginx.conf
# Rate limiting dos endpoints de autenticação.
# A diretriz `limit_req_zone` só é válida no contexto `http` — este arquivo é incluído
# dentro de `http {}` pelo nginx oficial (`include /etc/nginx/conf.d/*.conf;`).
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=20r/m;
limit_req_status 429;

server {
    listen 80;

    server_name localhost;

    # Headers de segurança para tudo que sai do proxy (inclusive estáticos servidos por alias)
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy same-origin always;
    add_header X-Frame-Options DENY always;

    # Content-Security-Policy: recomendado, porém exige nonce no script inline do
    # django-htmx ({% django_htmx_script %} lê `csp_nonce` do contexto). Habilite
    # somente após configurar o nonce — começando em report-only.
    # add_header Content-Security-Policy "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'self'" always;

    # client_max_body_size 50M;

    # Páginas de erro customizadas: HTML servidos de /etc/nginx/errors/ (bind mount
    # de staticfiles/errors/, populado pelo collectstatic a partir de core/static/errors/).
    error_page 400 401 402 /errors/400.html;
    error_page 403 /errors/403.html;
    error_page 404 /errors/404.html;
    error_page 500 502 503 504 /errors/500.html;

    location / {
        # Respostas 4xx/5xx do Django são substituídas pelas error_page acima —
        # sem isso, o mapeamento só valeria para erros gerados pelo próprio nginx.
        proxy_intercept_errors on;
        proxy_pass http://web:8000;
        # $http_host preserva a porta ($host a descarta): sem ela, links
        # gerados pelo Django (ativação/reset de senha) nascem sem a porta
        # e morrem em dev, onde o acesso canônico é localhost:8080.
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Autenticação com limite de tentativas: login, redefinição de senha (inclusive o
    # link com token) e login do admin. 20 requisições/min por IP, rajada de 5.
    # Excedeu o limite, o nginx responde 429 sem tocar no Django.
    location ~ ^/(accounts/(login|password_reset|reset)|admin/login)/ {
        limit_req zone=auth_limit burst=5 nodelay;

        proxy_pass http://web:8000;
        proxy_set_header Host $http_host;  # porta preservada, ver location /
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /code/staticfiles/;
    }

    # /media/ NÃO é público: `internal` bloqueia o acesso direto por URL.
    # Quando existir upload, sirva por uma view autenticada que valide a posse do
    # arquivo e devolva X-Accel-Redirect apontando para este location.
    location /media/ {
        internal;
        alias /code/media/;
    }

    # Páginas de erro das diretivas error_page. `internal` impede o acesso
    # direto a /errors/<arquivo> pela URL — só o próprio nginx as serve.
    location /errors/ {
        alias /etc/nginx/errors/;
        internal;
    }
}
```

**Notas sobre o `nginx.conf`**:

- **Rate limiting**: `auth_limit:10m` = 20 requisições/min por IP, com rajada de 5 (`burst=5 nodelay`); acima disso o nginx devolve **429**. Ajuste `rate`/`burst` conforme o tráfego real.
- ⚠️ **IP de origem atrás do Docker**: publicando a porta com o `docker-proxy`, o `$binary_remote_addr` visto pelo container pode ser o IP do gateway (todos os clientes contam no mesmo balde). Em produção, coloque o nginx atrás do balanceador real e configure `set_real_ip_from`/`real_ip_header X-Forwarded-For` para limitar por IP verdadeiro.
- **Headers**: `X-Content-Type-Options`, `Referrer-Policy` e `X-Frame-Options` são enviados em todas as respostas. O Django também envia `X-Frame-Options: DENY` (middleware de clickjacking); o header do nginx cobre os arquivos servidos por `alias`.
- **`/media/` internal**: o acesso direto à URL de um arquivo enviado é recusado pelo nginx. A autorização passa a ser obrigatória na aplicação (view autenticada + `X-Accel-Redirect`).
- **Páginas de erro customizadas**: `error_page` mapeia 400/401/402→`400.html`, 403→`403.html`, 404→`404.html` e 500/502/503/504→`500.html`, servidas de `/etc/nginx/errors/` (bind mount de `staticfiles/errors/`, populado pelo `collectstatic`). O `proxy_intercept_errors on` faz o nginx substituir também as respostas 4xx/5xx **vindas do Django** pelas páginas estáticas — o custo é perder qualquer contexto renderizado pelo framework no erro. O 429 do `limit_req` não tem página customizada e usa a página padrão do nginx.
- **`/errors/` internal**: as páginas não são acessíveis diretamente pela URL (`/errors/404.html` retorna 404); só o próprio nginx as serve via `error_page`.

**Páginas de erro do Nginx** — crie os quatro HTML em `core/static/errors/`. São arquivos autônomos (CSS inline, sem `base.html`/Tailwind): precisam renderizar mesmo com o Django fora do ar, inclusive no 502. O `collectstatic` da FASE 2 os copia para `staticfiles/errors/`, montado em `/etc/nginx/errors`.

`core/static/errors/400.html`:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>400 — Requisição Inválida</title>
    <style>
        *, *:before, *:after {
            box-sizing: border-box;
        }
        html {
            height: 100%;
        }
        body {
            font-family: sans-serif;
            background-color: #f2f2f2;
            height: 100%;
            padding: 10px;
        }
        a {
            color: #494949;
            text-decoration: none;
        }
        a:hover {
            color: #6b6b6b;
            text-decoration: none;
        }
        .text-wrapper {
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .title {
            font-size: 5em;
            font-weight: 700;
            color: #494949;
            text-align: center;
        }
        .subtitle {
            font-size: 40px;
            font-weight: 700;
            color: #6b6b6b;
            text-align: center;
        }
        .button {
            margin-top: 30px;
            font-weight: 700;
            border: 2px solid #494949;
            padding: 15px;
            text-transform: uppercase;
            color: #494949;
            border-radius: 26px;
            transition: all 0.2s ease-in-out;
            display: inline-block;
        }
        .button:hover {
            background-color: #494949;
            color: #f2f2f2;
        }
    </style>
</head>
<body>
    <div class="text-wrapper">
        <div class="title">
            400 - BAD REQUEST
        </div>
        <div class="subtitle">
            Oops, Requisição inválida.
        </div>
        <a class="button" href="/">Página Inicial</a>
    </div>
</body>
</html>
```

`core/static/errors/403.html`:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>403 — Acesso Negado</title>
    <style>
        *, *:before, *:after {
            box-sizing: border-box;
        }
        html {
            height: 100%;
        }
        body {
            font-family: sans-serif;
            background-color: #f2f2f2;
            height: 100%;
            padding: 10px;
        }
        a {
            color: #494949;
            text-decoration: none;
        }
        a:hover {
            color: #6b6b6b;
            text-decoration: none;
        }
        .text-wrapper {
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .title {
            font-size: 5em;
            font-weight: 700;
            color: #494949;
            text-align: center;
        }
        .subtitle {
            font-size: 40px;
            font-weight: 700;
            color: #6b6b6b;
            text-align: center;
        }
        .button {
            margin-top: 30px;
            font-weight: 700;
            border: 2px solid #494949;
            padding: 15px;
            text-transform: uppercase;
            color: #494949;
            border-radius: 26px;
            transition: all 0.2s ease-in-out;
            display: inline-block;
        }
        .button:hover {
            background-color: #494949;
            color: #f2f2f2;
        }
    </style>
</head>
<body>
    <div class="text-wrapper">
        <div class="title">
            403 - FORBIDDEN
        </div>
        <div class="subtitle">
            Oops, Acesso negado.
        </div>
        <a class="button" href="/">Página Inicial</a>
    </div>
</body>
</html>
```

`core/static/errors/404.html`:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>404 — Não Encontrado</title>
    <style>
        *, *:before, *:after {
            box-sizing: border-box;
        }
        html {
            height: 100%;
        }
        body {
            font-family: sans-serif;
            background-color: #f2f2f2;
            height: 100%;
            padding: 10px;
        }
        a {
            color: #494949;
            text-decoration: none;
        }
        a:hover {
            color: #6b6b6b;
            text-decoration: none;
        }
        .text-wrapper {
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .title {
            font-size: 5em;
            font-weight: 700;
            color: #494949;
            text-align: center;
        }
        .subtitle {
            font-size: 40px;
            font-weight: 700;
            color: #6b6b6b;
            text-align: center;
        }
        .button {
            margin-top: 30px;
            font-weight: 700;
            border: 2px solid #494949;
            padding: 15px;
            text-transform: uppercase;
            color: #494949;
            border-radius: 26px;
            transition: all 0.2s ease-in-out;
            display: inline-block;
        }
        .button:hover {
            background-color: #494949;
            color: #f2f2f2;
        }
    </style>
</head>
<body>
    <div class="text-wrapper">
        <div class="title">
            404 - NOT FOUND
        </div>
        <div class="subtitle">
            Oops, Recurso não encontrado.
        </div>
        <a class="button" href="/">Página Inicial</a>
    </div>
</body>
</html>
```

`core/static/errors/500.html`:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>500 — Erro Interno do Servidor</title>
    <style>
        *, *:before, *:after {
            box-sizing: border-box;
        }
        html {
            height: 100%;
        }
        body {
            font-family: sans-serif;
            background-color: #f2f2f2;
            height: 100%;
            padding: 10px;
        }
        a {
            color: #494949;
            text-decoration: none;
        }
        a:hover {
            color: #6b6b6b;
            text-decoration: none;
        }
        .text-wrapper {
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .title {
            font-size: 5em;
            font-weight: 700;
            color: #494949;
            text-align: center;
        }
        .subtitle {
            font-size: 40px;
            font-weight: 700;
            color: #6b6b6b;
            text-align: center;
        }
        .button {
            margin-top: 30px;
            font-weight: 700;
            border: 2px solid #494949;
            padding: 15px;
            text-transform: uppercase;
            color: #494949;
            border-radius: 26px;
            transition: all 0.2s ease-in-out;
            display: inline-block;
        }
        .button:hover {
            background-color: #494949;
            color: #f2f2f2;
        }
    </style>
</head>
<body>
    <div class="text-wrapper">
        <div class="title">
            500 - INTERNAL SERVER ERROR
        </div>
        <div class="subtitle">
            Oops, Erro interno do servidor.
        </div>
        <a class="button" href="/">Página Inicial</a>
    </div>
</body>
</html>
```

### 6. Exportar Requisitos

⚠️ **CRÍTICO**: o `Dockerfile` copia o `requirements.txt` para dentro da imagem. Este passo deve ser executado **antes** de qualquer `docker compose build`.

```bash
uv lock
uv export --no-dev --no-hashes --output-file requirements.txt
```

`requirements.txt` é um **export** do `pyproject.toml` (via `uv.lock`) e **nunca** deve ser editado à mão.

- `--no-dev` é intencional: as dependências de desenvolvimento (`pytest`, `pytest-django`, `pytest-cov`, `ruff`, `taskipy`, `django-extensions`) rodam no host e não entram na imagem — isso mantém ferramentas poderosas de depuração fora do runtime.
- O export é feito **com `--no-hashes`**: o `requirements.txt` não contém hashes e o `Dockerfile` instala com `pip install` simples (sem `--require-hashes`). A fixação exata de versões continua garantida pelo `uv.lock`.

---

## Tailwind CSS v4 Standalone, HTMX e Templates

Esta seção documenta o Tailwind CSS v4 usando o CLI standalone (sem Node.js), o HTMX, as tasks do Taskipy, os templates e as views/URLs/Celery.

### 1. Criar a Estrutura de Diretórios

```bash
mkdir -p core/static/core/css
mkdir -p core/static/core/js/htmx
mkdir -p templates
```

### 2. STATICFILES_DIRS

⚠️ **CRÍTICO**: o `STATICFILES_DIRS` já está aplicado no `core/settings.py` completo da seção [Modelo de Usuário Customizado](#5-substituir-coresettingspy-por-completo):

```python
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'core' / 'static',
]
```

**Explicação**: o Django coleta arquivos estáticos apenas de apps registrados no `INSTALLED_APPS`. Como `core` é o projeto e não um app, o diretório `core/static/` é ignorado pelo `collectstatic`. Sem o `STATICFILES_DIRS`, o `collectstatic --noinput` copia apenas os estáticos de `admin` e `django_htmx` para `staticfiles/`, mas **não** copia `core/static/core/css/output.css` nem `core/static/core/js/htmx/htmx.min.js`. O Nginx serve apenas o que está em `staticfiles/`, resultando em HTTP 404 para o CSS e JS do Tailwind/HTMX.

### 3. Baixar HTMX

⚠️ **IMPORTANTE**: baixe sempre a versão mais recente do HTMX. **Versão usada por este guia**: 2.0.9.

```bash
# Criar diretório para o HTMX
mkdir -p core/static/core/js/htmx

# Baixar versão mais recente do HTMX (2.0.9)
curl -sL https://unpkg.com/htmx.org@2.0.9/dist/htmx.min.js -o core/static/core/js/htmx/htmx.min.js
```

**Verificação**: o arquivo baixado deve ter ~51 KB:

```bash
wc -c core/static/core/js/htmx/htmx.min.js
```

**Verificar versões disponíveis**: https://htmx.org/ · https://github.com/bigskysoftware/htmx/releases · https://unpkg.com/htmx.org/ · https://www.jsdelivr.com/package/npm/htmx.org

**URL alternativa** (substitua `X.X.X` pela versão desejada):

```bash
curl -sL https://unpkg.com/htmx.org@X.X.X/dist/htmx.min.js -o core/static/core/js/htmx/htmx.min.js
```

⚠️ **NOTA**: o template `base.html` referencia o HTMX **exatamente** em `core/static/core/js/htmx/htmx.min.js`:

```html
<script src="{% static 'core/js/htmx/htmx.min.js' %}" defer></script>
```

### 4. Criar Arquivo CSS de Entrada

Crie `core/static/core/css/input.css`:

```css
@import "tailwindcss";

/* Custom styles for Django */
@layer base {
  body {
    @apply bg-gray-50 text-gray-900 antialiased;
  }
}

@layer components {
  .btn {
    @apply px-4 py-2 rounded-lg font-medium transition-colors duration-200 inline-block cursor-pointer border-0;
  }
  
  .btn-primary {
    @apply px-4 py-2 rounded-lg font-medium transition-colors duration-200 inline-block cursor-pointer border-0 bg-blue-600 text-white hover:bg-blue-700;
  }
  
  .btn-secondary {
    @apply px-4 py-2 rounded-lg font-medium transition-colors duration-200 inline-block cursor-pointer border-0 bg-gray-200 text-gray-800 hover:bg-gray-300;
  }
  
  .card {
    @apply bg-white rounded-lg shadow-md p-6;
  }
  
  .form-input {
    @apply w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none;
  }
}
```

### 5. Configurar o pyproject.toml

Adicione ao `pyproject.toml` (o arquivo já contém `[project]` e `[dependency-groups]` criados pelo uv):

```toml
[tool.taskipy.tasks]
# Tasks via Docker - Funcionam em qualquer ambiente
css-build = { cmd = "docker compose exec web tailwindcss -i /code/core/static/core/css/input.css -o /code/core/static/core/css/output.css --minify", help = "Build Tailwind CSS for production via Docker" }
css-watch = { cmd = "docker compose exec web tailwindcss -i /code/core/static/core/css/input.css -o /code/core/static/core/css/output.css --watch", help = "Watch and rebuild Tailwind CSS via Docker" }
css-dev = { cmd = "docker compose exec web tailwindcss -i /code/core/static/core/css/input.css -o /code/core/static/core/css/output.css", help = "Build Tailwind CSS for development via Docker" }

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "core.settings"
python_files = ["tests.py", "test_*.py", "*_tests.py"]
norecursedirs = [".*", "*.egg", "build", "dist", "node_modules", "data", ".venv", "staticfiles", "media"]
```

**Notas**:

- As tasks do Tailwind executam **via Docker** (o CLI está instalado na imagem, seção 8) e exigem os containers no ar: `docker compose up -d`.
- `DJANGO_SETTINGS_MODULE` + `pytest-django` fazem o pytest configurar o Django automaticamente. Sem eles, qualquer teste que importe models/templates falha.
- `norecursedirs` reproduz a lista padrão do pytest e adiciona os diretórios deste projeto — em especial **`data`**, que contém o datadir do PostgreSQL montado em `./data/db` e quebraria a coleta (`exit 2`).

### 6. Scripts de Build (Opcional - Execução Local)

⚠️ **OPCIONAL**: o método recomendado é usar as tasks via Docker (passo 5). Estes scripts só são necessários para rodar o Tailwind **fora** do Docker e exigem baixar o CLI para `bin/` (ver abaixo).

```bash
mkdir -p scripts
```

**Baixar o CLI localmente (opcional)** — Linux:

```bash
mkdir -p bin
curl -sLO "https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64"
mv tailwindcss-linux-x64 bin/tailwindcss
chmod +x bin/tailwindcss
```

Windows (PowerShell):

```powershell
mkdir -p bin
Invoke-WebRequest -Uri "https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-windows-x64.exe" -OutFile "bin/tailwindcss.exe"
```

macOS:

```bash
mkdir -p bin
curl -sLO "https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-macos-x64"
mv tailwindcss-macos-x64 bin/tailwindcss
chmod +x bin/tailwindcss
```

**`scripts/build-css.sh`** (Linux/macOS):

```bash
#!/bin/bash
# Build Tailwind CSS for production (requer ./bin/tailwindcss)
echo "Building Tailwind CSS..."
./bin/tailwindcss -i ./core/static/core/css/input.css -o ./core/static/core/css/output.css --minify
echo "Build complete!"
```

**`scripts/watch-css.sh`** (Linux/macOS):

```bash
#!/bin/bash
# Watch Tailwind CSS (requer ./bin/tailwindcss)
echo "Starting Tailwind CSS watcher..."
echo "Press Ctrl+C to stop"
./bin/tailwindcss -i ./core/static/core/css/input.css -o ./core/static/core/css/output.css --watch
echo "Watcher stopped."
```

**`scripts/build-css.bat`** (Windows):

```batch
@echo off
echo Building Tailwind CSS...
".\bin\tailwindcss.exe" -i "core\static\core\css\input.css" -o "core\static\core\css\output.css" --minify
if %errorlevel% neq 0 (
    echo Error: Build failed!
    exit /b 1
)
echo Build complete!
```

**`scripts/watch-css.bat`** (Windows):

```batch
@echo off
echo Starting Tailwind CSS watcher...
echo Press Ctrl+C to stop
".\bin\tailwindcss.exe" -i "core\static\core\css\input.css" -o "core\static\core\css\output.css" --watch
echo Watcher stopped.
```

**Torne os scripts Linux/macOS executáveis:**

```bash
chmod +x scripts/build-css.sh scripts/watch-css.sh
```

### 7. Criar os Templates Django

#### 7.1 Template Base (`templates/base.html`)

Substitua `[nome_do_projeto]` pelo basename do diretório raiz:

```html
{% load static %}
{% load django_htmx %}
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}[nome_do_projeto]{% endblock %}</title>
    <link rel="stylesheet" href="{% static 'core/css/output.css' %}">
    <!-- HTMX: allowEval desligado (htmx não avalia JavaScript de atributos hx-*) -->
    <meta name="htmx-config" content='{"allowEval": false}'>
    <script src="{% static 'core/js/htmx/htmx.min.js' %}" defer></script>  
    {% django_htmx_script %}
    {% block extra_css %}{% endblock %}
</head>
<body class="min-h-screen flex flex-col" hx-headers='{"x-csrftoken": "{{ csrf_token }}"}'>
    <!-- Navigation -->
    <nav class="bg-white shadow-sm">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16">
                <div class="flex items-center">
                    <a href="{% url 'home' %}" class="text-2xl font-bold text-blue-600">
                        [nome_do_projeto]
                    </a>
                </div>
                <div class="flex items-center space-x-4">
                    {% if user.is_authenticated %}
                        <span class="text-gray-700">Olá, {{ user.username }}</span>
                        <form method="post" action="{% url 'logout' %}" class="inline">
                            {% csrf_token %}
                            <button type="submit" class="btn-secondary">Sair</button>
                        </form>
                    {% else %}
                        <a href="{% url 'login' %}" class="btn-primary">Entrar</a>
                    {% endif %}
                </div>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="flex-grow max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        {% block content %}{% endblock %}
    </main>

    <!-- Footer -->
    <footer class="bg-gray-800 text-white py-6 mt-auto">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <p>&copy; 2026 [nome_do_projeto]. Todos os direitos reservados.</p>
        </div>
    </footer>

    {% block extra_js %}{% endblock %}
</body>
</html>
```

#### 7.2 Template Home (`templates/home.html`)

Substitua `[nome_do_projeto]` pelo basename do diretório raiz:

```html
{% extends 'base.html' %}

{% block title %}Home - [nome_do_projeto]{% endblock %}

{% block content %}
<div class="text-center py-20">
    <h1 class="text-5xl font-bold text-gray-900 mb-6">
        Bem-vindo ao [nome_do_projeto]
    </h1>
    <p class="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
        Sistema desenvolvido com Django 5.2 e Tailwind CSS v4.
    </p>
    
    <div class="flex justify-center gap-4">
        {% if user.is_staff %}
            <a href="{% url 'admin:index' %}" class="btn-primary text-lg">
                Acessar Admin
            </a>
        {% elif user.is_authenticated %}
            <p class="text-gray-600">Sessão iniciada como {{ user.username }}.</p>
        {% else %}
            <a href="{% url 'login' %}" class="btn-primary text-lg">
                Entrar no Sistema
            </a>
        {% endif %}
    </div>
</div>

<!-- Features Section -->
<div class="grid md:grid-cols-3 gap-8 mt-16">
    <div class="card">
        <div class="text-blue-600 text-4xl mb-4">🚀</div>
        <h3 class="text-xl font-semibold mb-2">Moderno</h3>
        <p class="text-gray-600">Desenvolvido com as mais recentes tecnologias.</p>
    </div>
    
    <div class="card">
        <div class="text-blue-600 text-4xl mb-4">⚡</div>
        <h3 class="text-xl font-semibold mb-2">Rápido</h3>
        <p class="text-gray-600">Performance otimizada com Django e Tailwind.</p>
    </div>
    
    <div class="card">
        <div class="text-blue-600 text-4xl mb-4">🔒</div>
        <h3 class="text-xl font-semibold mb-2">Seguro</h3>
        <p class="text-gray-600">Autenticação e autorização robustas.</p>
    </div>
</div>
{% endblock %}
```

#### 7.3 Template de Login (`templates/registration/login.html`)

⚠️ **CRÍTICO**: `django.contrib.auth.urls` (seção 9, `core/urls.py`) resolve `/accounts/login/` para a `LoginView`, que procura **`registration/login.html`**. Sem este arquivo, `/accounts/login/` responde **HTTP 500** (`TemplateDoesNotExist: registration/login.html`).

Substitua `[nome_do_projeto]` pelo basename do diretório raiz:

```html
{% extends 'base.html' %}

{% block title %}Entrar - [nome_do_projeto]{% endblock %}

{% block content %}
<div class="max-w-md mx-auto mt-16">
    <div class="card">
        <h1 class="text-2xl font-semibold mb-6 text-center">Entrar</h1>

        {% if form.errors %}
            <p class="text-red-600 mb-4">Usuário ou senha inválidos.</p>
        {% endif %}

        <form method="post" class="space-y-4">
            {% csrf_token %}
            <div>
                <label for="{{ form.username.id_for_label }}" class="block text-sm font-medium mb-1">Usuário</label>
                <input type="text" name="{{ form.username.html_name }}" id="{{ form.username.id_for_label }}" class="form-input" autofocus required>
            </div>
            <div>
                <label for="{{ form.password.id_for_label }}" class="block text-sm font-medium mb-1">Senha</label>
                <input type="password" name="{{ form.password.html_name }}" id="{{ form.password.id_for_label }}" class="form-input" required>
            </div>
            <input type="hidden" name="next" value="{{ next }}">
            <button type="submit" class="btn-primary w-full">Entrar</button>
        </form>
    </div>
</div>
{% endblock %}
```

### 8. Criar View para Home

Crie `core/views.py`:

```python
from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = 'home.html'
```

### 9. Configurar URLs

Edite `core/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import HomeView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', HomeView.as_view(), name='home'),
    path('accounts/', include('django.contrib.auth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### 10. Configurar Celery

Crie `core/celery.py`:

```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

Edite `core/__init__.py`:

```python
from __future__ import absolute_import, unicode_literals
from .celery import app as celery_app

__all__ = ('celery_app',)
```

**Nota**: o broker vem de `CELERY_BROKER_URL` no `settings.py` (lido do `.env`), e o worker do compose executa `celery -A core worker --loglevel=info`.

---

## EXECUÇÃO OBRIGATÓRIA DO PROJETO

⚠️ **INSTRUÇÃO CRÍTICA**: o projeto **NÃO** está completo até que as quatro fases abaixo sejam 100% executadas, **na ordem**, sem erros. Este é o **único** runbook de execução do guia.

### FASE 1: Configuração (checklist)

Confira que cada artefato das seções 4 a 9 existe antes de seguir para a FASE 2:

- [ ] `uv init --python 3.13` + `uv venv` + `main.py` removido
- [ ] `.gitignore` gerado por `ignr -n django` com os itens adicionados
- [ ] `.vscode/settings.json`
- [ ] `pyproject.toml` com `requires-python = ">=3.13,<4.0"`, `[tool.taskipy.tasks]` e `[tool.pytest.ini_options]`
- [ ] Dependências instaladas (runtime, dev e Celery) e `uv sync` executado — `django-extensions` **apenas** no grupo dev
- [ ] Projeto Django criado (`manage.py`, `core/`)
- [ ] `.env.example` criado e `.env` copiado a partir dele
- [ ] `SECRET_KEY`, `DB_PASS` e `REDIS_PASSWORD` gerados no `.env` (passo 2 da seção Configuração do Ambiente)
- [ ] `.env` com permissão `600` e ignorado pelo git; `.env.example` (sem segredos) adicionado ao git
- [ ] App `accounts` com `User(AbstractUser)` e `UserAdmin`
- [ ] `core/base_models/` (`__init__.py`, `mixins.py`, `models.py`)
- [ ] `core/settings.py` substituído pelo conteúdo completo da seção 7
- [ ] `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `nginx.conf`
- [ ] `data/`, `media/`, `staticfiles/`, `staticfiles/errors/` criados
- [ ] `requirements.txt` exportado **sem hashes** (`uv lock` + `uv export --no-dev --no-hashes`)
- [ ] `core/static/core/css/input.css` e `core/static/core/js/htmx/htmx.min.js`
- [ ] `core/static/errors/{400,403,404,500}.html` (páginas de erro do Nginx)
- [ ] `templates/base.html`, `templates/home.html`, `templates/registration/login.html`
- [ ] `core/views.py`, `core/urls.py`, `core/celery.py`, `core/__init__.py`

### FASE 2: Execução

```bash
# 1. Garantir que não existe banco SQLite residual
rm -f db.sqlite3

# 2. Compilar as imagens e subir os serviços
docker compose up -d --build

# 3. Criar e aplicar as migrações (no container, para usar o PostgreSQL)
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

# 4. Compilar o Tailwind CSS (grava core/static/core/css/output.css no host)
uv run task css-build

# 5. Verificar recursivamente que o output.css foi gerado
find core/static -name output.css -ls

# 6. Coletar os arquivos estáticos para o Nginx
docker compose exec web python manage.py collectstatic --noinput

# 7. Gerar uma senha FORTE e única para o superusuário (nenhuma senha default é documentada)
uv run python - <<'PY'
import pathlib
import secrets

arquivo = pathlib.Path('.superuser-password')
arquivo.write_text(secrets.token_urlsafe(24) + '\n')
arquivo.chmod(0o600)
print('senha do superusuário gravada em .superuser-password (modo 600)')
PY

# 8. Criar o superusuário usando a senha gerada
docker compose exec -e DJANGO_SUPERUSER_PASSWORD="$(cat .superuser-password)" web \
  python manage.py createsuperuser --noinput --username system --email admin@example.com

# 9. Verificar no banco de dados que o usuário "system" foi criado
docker compose exec db psql -U postgres -c "SELECT username, is_superuser FROM accounts_user;"
```

⚠️ **Sobre a senha do superusuário**: `createsuperuser --noinput` **não** executa os `AUTH_PASSWORD_VALIDATORS` (o modo interativo executa). Por isso o guia **gera** uma senha aleatória forte em vez de aceitar uma escolhida à mão. Guarde-a em um gerenciador de segredos e apague o arquivo temporário ao final ([FASE 4](#fase-4-versionamento---commit-inicial)). Nunca escreva a senha em documento, issue, README ou mensagem de commit.

**Resultados esperados**:

- Passo 2: os cinco serviços `Up` (`db` com `(healthy)`).
- Passo 3: `Migrations for 'accounts': accounts/migrations/0001_initial.py` e todas as migrações `OK`.
- Passo 4: `≈ tailwindcss v4.1.18` e `Done in ...`.
- Passo 5: uma linha com `core/static/core/css/output.css` (≈ 15 KB).
- Passo 6: `N static files copied to '/code/staticfiles'.`
- Passo 7: `senha do superusuário gravada em .superuser-password (modo 600)`.
- Passo 8: `Superuser created successfully.`
- Passo 9: uma linha com `system|t`.

⚠️ **Criou ou alterou algum template depois do passo 2?** Execute `docker compose restart web` antes de testar a rota correspondente. O Django 5.2 envolve os template loaders em `cached.Loader` **incondicionalmente**, então um template que não existia no primeiro acesso fica cacheado como ausente até o processo do `runserver` reiniciar (ver [Solução de Problemas](#erro-http-500-com-templatedoesnotexist-mesmo-após-criar-o-template)).

### FASE 3: Verificação

```bash
# Logs dos cinco serviços
docker compose logs --tail 50 web
docker compose logs --tail 50 db
docker compose logs --tail 50 redis
docker compose logs --tail 50 worker
docker compose logs --tail 50 nginx
```

```bash
# Configuração e migrações do Django
docker compose exec web python manage.py check
docker compose exec web python manage.py showmigrations

# Arquivo estático coletado
docker compose exec web ls -la /code/staticfiles/core/css/output.css

# Nginx respondendo internamente
docker compose exec nginx curl -s -o /dev/null -w "%{http_code}\n" http://localhost/
```

```bash
# Endpoints (Nginx :8080 é o canônico)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/accounts/login/
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/static/core/css/output.css
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/static/core/js/htmx/htmx.min.js

# Acesso direto ao Django (debug, sem Nginx)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
```

**Resultados esperados**:

| Verificação | Saída esperada |
|---|---|
| `manage.py check` | `System check identified no issues (0 silenced).` |
| `showmigrations` | todas as migrações marcadas com `[X]` |
| `ls -la /code/staticfiles/core/css/output.css` | arquivo presente (≈ 15 KB) |
| `curl` interno do Nginx | `200` |
| `http://localhost:8080/` | `200` |
| `http://localhost:8080/accounts/login/` | `200` |
| `http://localhost:8080/static/core/css/output.css` | `200` |
| `http://localhost:8080/static/core/js/htmx/htmx.min.js` | `200` |
| `http://localhost:8000/` | `200` |
| `manage.py check` com segredo ausente/inseguro ou `DEBUG` inseguro | falha (`ImproperlyConfigured`) |
| `curl http://localhost:8080/media/qualquer-arquivo.txt` | `404` |
| rajada de POSTs em `/accounts/login/` | contém `429` |

**Verificação adicional (login autenticado de ponta a ponta)**:

```bash
rm -f /tmp/cookies.txt /tmp/login.html
curl -s -o /tmp/login.html -c /tmp/cookies.txt http://localhost:8080/accounts/login/
TOKEN=$(sed -n 's/.*name="csrfmiddlewaretoken" value="\([^"]*\)".*/\1/p' /tmp/login.html | sed -n '1p')
curl -s -b /tmp/cookies.txt -c /tmp/cookies.txt -o /dev/null -w "%{http_code}\n" \
  -e http://localhost:8080/accounts/login/ \
  -d "username=system&password=$(cat .superuser-password)&csrfmiddlewaretoken=${TOKEN}" \
  http://localhost:8080/accounts/login/
```

Saída esperada: `302` (redirecionamento para `home` após autenticar). Um `200` aqui significa que as credenciais foram rejeitadas.

**Verificação dos controles de segurança (cada um deve FALHAR de propósito)**

Os quatro primeiros comandos devem terminar com erro explícito (`ImproperlyConfigured`) — é exatamente isso que impede um novo projeto de subir inseguro:

```bash
# 1. SECRET_KEY ausente
docker compose exec -e SECRET_KEY= web python manage.py check

# 2. SECRET_KEY insegura (chave gerada pelo startproject / placeholder)
docker compose exec -e SECRET_KEY=django-insecure-troque-me web python manage.py check

# 3. DEBUG=True com host que não é local
docker compose exec -e DEBUG=True -e ALLOWED_HOSTS=exemplo.com web python manage.py check

# 4. DEBUG=False sem as flags de cookie/TLS
docker compose exec -e DEBUG=False web python manage.py check

# 5. A configuração real do projeto continua válida
docker compose exec web python manage.py check
```

```bash
# 6. /media/ não é público (deve responder 404)
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/media/qualquer-arquivo.txt

# 7. Rate limiting em autenticação (deve aparecer 429 na rajada)
for i in $(seq 1 12); do
  curl -s -o /dev/null -w "%{http_code} " -X POST -d "username=x&password=y" http://localhost:8080/accounts/login/
done; echo
```

**Resultados esperados**: comandos 1–4 terminam com código de saída diferente de zero e mensagem `django.core.exceptions.ImproperlyConfigured`; comando 5 imprime `System check identified no issues`; comando 6 imprime `404`; comando 7 imprime uma sequência que contém `429` após a rajada permitida.

### FASE 4: Versionamento - commit inicial

⚠️ O commit inicial deve ser executado **apenas no fim do projeto**, depois de todas as fases acima.

```bash
# .env NÃO deve aparecer na saída
git status --short

# Confirmar a regra que ignora o .env
git check-ignore -v .env

# Confirmar que o .env.example está rastreado
git ls-files --error-unmatch .env.example

# Confirmar que o arquivo temporário de senha está ignorado
git check-ignore -v .superuser-password

# Guardar a senha do superusuário no gerenciador de segredos e apagar o arquivo temporário
rm -f .superuser-password

# Commit inicial
git add -A && git commit -m "feat: initial commit"
```

**Resultados esperados**:

- `git status --short` **não** lista `.env` (mas lista `.env.example` como novo arquivo).
- `git check-ignore -v .env` mostra a linha do `.gitignore` que casa com `.env`.
- `git ls-files --error-unmatch .env.example` imprime `.env.example`.
- `git check-ignore -v .superuser-password` mostra a linha do `.gitignore` que casa com o arquivo.
- A senha está no gerenciador de segredos e `.superuser-password` foi removido (nenhum segredo no commit).
- O commit é criado sem erros.

---

## Notas Importantes

### Estrutura do Projeto

```
[nome_do_projeto]/
├── accounts/                    # App de Usuário customizado
│   ├── models.py               # Modelo de Usuário customizado
│   ├── admin.py                # UserAdmin
│   └── migrations/             # 0001_initial.py (criado na FASE 2)
├── core/                        # Projeto Django
│   ├── settings.py             # Configurações completas (env + BD dinâmica)
│   ├── urls.py
│   ├── wsgi.py
│   ├── views.py                # HomeView
│   ├── celery.py               # Configuração Celery
│   ├── base_models/            # Mixins e modelo base abstrato
│   └── static/                 # Arquivos estáticos (inclui Tailwind e HTMX)
│       ├── core/
│       │   ├── css/
│       │   │   ├── input.css
│       │   │   └── output.css  # Gerado por `uv run task css-build` (não versionado)
│       │   └── js/
│       │       └── htmx/
│       │           └── htmx.min.js
│       └── errors/             # Páginas de erro do Nginx (servidas de /etc/nginx/errors)
│           ├── 400.html
│           ├── 403.html
│           ├── 404.html
│           └── 500.html
├── templates/                  # Templates Django
│   ├── base.html
│   ├── home.html
│   └── registration/
│       └── login.html          # OBRIGATÓRIO para /accounts/login/
├── scripts/                    # Scripts de build (OPCIONAIS - execução local)
│   ├── build-css.bat
│   ├── watch-css.bat
│   ├── build-css.sh
│   └── watch-css.sh
├── bin/                        # Binários locais do Tailwind (OPCIONAL)
│
├── .vscode/                    # Definições do VSCode
├── data/                       # Dados do PostgreSQL (Docker) - ignorado no git
├── media/                      # Uploads de usuários
├── staticfiles/                # Arquivos estáticos coletados - ignorado no git
│   └── errors/                 # Populado pelo collectstatic (core/static/errors/); montado em /etc/nginx/errors
├── .env                        # Variáveis de ambiente — segredos gerados, modo 600 (NÃO commitar!)
├── .superuser-password         # TEMPORÁRIO (FASE 2): senha gerada do superusuário; modo 600, ignorado pelo git, apagar ao final
├── .env.example                # Template de variáveis de ambiente (COMMITAR)
├── .dockerignore               # Arquivo de ignorar do Docker
├── .gitignore                  # Arquivo de ignorar do Git
├── Dockerfile                  # Configuração de imagem Docker (com Tailwind)
├── nginx.conf                  # Configuração do Nginx
├── docker-compose.yml          # Orquestração dos cinco serviços
├── manage.py                   # CLI do Django
├── uv.lock                     # Arquivo de lock do uv
├── pyproject.toml              # Configuração do uv (tasks Tailwind + pytest)
├── requirements.txt            # Requisitos Python (export do uv)
└── .venv                       # Ambiente virtual
```

**Arquivos OBRIGATÓRIOS:**

- `.env.example` - Template seguro para versionamento (substitui `.env` no git)
- `templates/registration/login.html` - Sem ele, `/accounts/login/` responde HTTP 500

**Arquivos OPCIONAIS:**

- `bin/` - CLI do Tailwind para execução local (o fluxo recomendado usa o CLI dentro do container)
- `scripts/*.bat` - Scripts de build para Windows
- `scripts/*.sh` - Scripts de build para Linux/macOS

### Ajustes-Chave Realizados

1. **Versão Python única**: **3.13** no ambiente virtual (`uv venv --python 3.13`), no `requires-python` (`>=3.13,<4.0`) e na imagem (`python:3.13-slim`). O limite superior `<4.0` acompanha o `Requires-Python` do `taskipy` (`>=3.6,<4.0`).
2. **Versão Django**: 5.2.x (LTS, suporte até abril/2028). Alternativa documentada: 6.1.x (requer Python >=3.12) — **não validada** neste guia.
3. **Configuração de Banco de Dados**: alternância dinâmica por `DB_ENGINE` — `postgresql` usa PostgreSQL (configuração padrão do `.env`); qualquer outro valor (ou ausente) usa SQLite local.
4. **`.env` sem nenhum segredo utilizável**: `.env.example` traz apenas chaves vazias (`SECRET_KEY=`, `DB_PASS=`, `REDIS_PASSWORD=`); os valores são **gerados** por máquina no passo 2 da seção [Configuração do Ambiente](#configuração-do-ambiente) e gravados apenas no `.env` (modo `600`). Sem `.env` o Compose aborta; com `DB_PASS` vazio o container `db` não inicializa — os dois modos de falha são explícitos, nunca silenciosos.
5. **CSRF_TRUSTED_ORIGINS**: com prefixo de esquema (`http://`, `https://`).
6. **Worker do Celery**: comando usa `-A core`.
7. **Internacionalização**: Português Brasileiro (`pt-br`, `America/Sao_Paulo`).
8. **HTMX**: 2.0.9 + `django_htmx` em `INSTALLED_APPS` e `HtmxMiddleware` em `MIDDLEWARE`.
9. **Tailwind CSS v4**: CLI standalone (sem Node.js), instalado na imagem **e** executado no host pela task `css-build` (o bind mount `.:/code` sombreia o artefato gerado no build da imagem).
10. **STATICFILES_DIRS**: configuração obrigatória para que o `collectstatic` encontre `core/static/` e o Nginx sirva o CSS/JS.
11. **Template de login**: `templates/registration/login.html` é obrigatório para a `LoginView` do `django.contrib.auth.urls`.
12. **`cached.Loader` do Django 5.2**: o engine de templates envolve os loaders em `cached.Loader` incondicionalmente; um template ausente no primeiro acesso fica cacheado como ausente. Após criar/alterar templates, `docker compose restart web`.
13. **pytest configurado**: `pytest-django` + `DJANGO_SETTINGS_MODULE` + `norecursedirs` (exclui `data/`, que contém o datadir do PostgreSQL e quebraria a coleta).
14. **Superusuário com senha forte gerada em runtime**: `createsuperuser --noinput` com `DJANGO_SUPERUSER_PASSWORD` lido de `.superuser-password` (modo `600`, ignorado pelo git e apagado ao final). Nenhuma senha fixa é documentada. O modo interativo executa os `AUTH_PASSWORD_VALIDATORS`; o modo `--noinput` **não** executa — por isso a senha é aleatória e longa, não escolhida à mão.
15. **Sem segredo default**: `SECRET_KEY` sem fallback (ausência/insegurança = `ImproperlyConfigured`), `DB_PASS` e `REDIS_PASSWORD` gerados por máquina, Redis com `--requirepass`.
16. **Guardrails de startup**: `settings.py` recusa subir com `SECRET_KEY` ausente/placeholder, `ALLOWED_HOSTS` com `*`, `DEBUG=True` com host não local e `DEBUG=False` sem `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE`/`SECURE_SSL_REDIRECT`.
17. **Integridade de artefatos**: imagens `postgres`/`redis`/`nginx` por digest sha256 e binário do Tailwind verificado por `sha256sum -c` (dependências Python fixadas pelo `uv.lock` e exportadas **sem** hashes).
18. **Nginx endurecido**: rate limiting (`20r/m`, `burst=5`, status `429`) em `login`, redefinição de senha e login do admin; headers `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`; `/media/` como `internal` (nunca público).
19. **Runtime mínimo**: `django-extensions` só no grupo dev (fora da imagem e do `INSTALLED_APPS`); HTMX com `allowEval: false`; link do admin renderizado apenas para `user.is_staff`.
20. **Portas**: `127.0.0.1` para `5432` e `8000`; `8080` (Nginx, porta canônica) publicada em todas as interfaces para acesso pela rede; o acesso entre serviços usa a rede interna do Compose.

### Comandos Docker

| Objetivo | Comando |
|---|---|
| Compilar e iniciar | `docker compose up -d --build` |
| Executar migrações | `docker compose exec web python manage.py migrate` |
| Criar migrações | `docker compose exec web python manage.py makemigrations` |
| Criar superusuário | `uv run python -c "import pathlib,secrets; f=pathlib.Path('.superuser-password'); f.write_text(secrets.token_urlsafe(24)); f.chmod(0o600)"` e depois `docker compose exec -e DJANGO_SUPERUSER_PASSWORD="$(cat .superuser-password)" web python manage.py createsuperuser --noinput --username system --email admin@example.com` |
| Coletar arquivos estáticos | `docker compose exec web python manage.py collectstatic --noinput` |
| Ver logs (seguindo) | `docker compose logs -f web` |
| Parar serviços | `docker compose stop` |
| Remover serviços | `docker compose down` |

**Nota**: em contextos **sem TTY** (CI, scripts), acrescente `-T` aos comandos `exec`/`run` (ex.: `docker compose exec -T web python manage.py migrate`).

### Comandos Tailwind CSS

| Objetivo | Comando |
|---|---|
| Build para produção (minificado) | `uv run task css-build` |
| Build para desenvolvimento (não minificado) | `uv run task css-dev` |
| Watch mode (recompila automaticamente) | `uv run task css-watch` |
| Equivalente direto (sem taskipy) | `docker compose exec web tailwindcss -i /code/core/static/core/css/input.css -o /code/core/static/core/css/output.css --minify` |

**Pré-requisito**: os containers Docker devem estar em execução (`docker compose up -d`).

### Fluxo de Desenvolvimento

1. **Adicionar Dependências**: ver [Fluxo Obrigatório: Adicionar Dependências Python](#fluxo-obrigatório-adicionar-dependências-python).

2. **Criar Apps**:

   ```bash
   uv run python manage.py startapp nomeapp
   # Adicione a INSTALLED_APPS em core/settings.py
   ```

3. **Atualizar CSS (Tailwind)**:

   ```bash
   uv run task css-watch   # durante o desenvolvimento
   uv run task css-build   # antes de commitar mudanças de CSS/templates

   docker compose exec web python manage.py collectstatic --noinput
   ```

   ⚠️ Ao criar um **novo template**, rode `docker compose restart web` (ver `cached.Loader` em [Ajustes-Chave](#ajustes-chave-realizados)).

4. **Executar Testes**:

   ```bash
   uv run pytest
   ```

   **Nota**: sem nenhum teste escrito, o pytest termina com `no tests ran` (exit code 5) — isso é esperado. Os testes ficam em `accounts/tests.py` ou em arquivos `test_*.py` / `*_tests.py`.

5. **Qualidade de Código**:

   ```bash
   uv run ruff check .
   uv run ruff format .
   ```

### Melhores Práticas

1. ✅ SEMPRE use uv para gerenciamento de dependências
2. ✅ **JAMAIS edite requirements.txt manualmente** - é um export do pyproject.toml
3. ✅ **JAMAIS instale libs com pip install** - sempre use `uv add`
4. ✅ **SEMPRE rebuild do Docker após mudar requirements.txt** (`docker compose up -d --build`)
5. ✅ **SEMPRE reinicie nginx após rebuild do web** (`docker compose restart nginx`)
6. ✅ **SEMPRE reinicie web após criar/alterar templates** (`docker compose restart web`)
7. ✅ **NUNCA faça commit de arquivos sensíveis** (.env, db.sqlite3)
8. ✅ **SEMPRE use .env.example no git, nunca .env**
9. ✅ Siga convenções de mensagem de commit: `feat:`, `fix:`, `refactor:`
10. ✅ Use `.venv` criado pelo uv na raiz do projeto
11. ✅ NUNCA mude `AUTH_USER_MODEL` após as migrações serem criadas
12. ✅ Execute `uv run task css-build` (via Docker) antes de fazer commit de mudanças no CSS
13. ✅ Use `uv run task css-watch` (via Docker) durante desenvolvimento para auto-reload
14. ✅ Realize o commit inicial apenas na conclusão de toda implementação, execução e testes
15. ✅ **Use o checklist de dependências** sempre que adicionar novas bibliotecas
16. ✅ **Verifique se .env está no .gitignore** antes de fazer commit
17. ✅ Arquivos criados **dentro do container** (migrações, `output.css`) podem ficar com owner diferente do seu usuário no host (ex.: `root`, `nobody`) — ver [Solução de Problemas](#erro-arquivos-gerados-pelo-container-ficam-com-owner-diferente-do-seu-usuário-no-host-ex-root-nobody)
18. ✅ **NUNCA** coloque segredo em código, `.env.example`, documentação, issue ou mensagem de commit — segredos vivem só no `.env` (modo `600`) ou em gerenciador de segredos
19. ✅ **NUNCA** crie usuário com senha fixa (mesmo em desenvolvimento): gere com `secrets.token_urlsafe` e guarde no gerenciador de segredos
20. ✅ **NUNCA** remova as validações de startup do `settings.py` nem a verificação sha256/digest para "fazer subir" — ajuste a configuração, não o controle
21. ✅ **Mantenha `DEBUG=False`** em qualquer ambiente alcançável pela rede; `DEBUG=True` só com hosts locais
22. ✅ **Revise o `check --deploy`** antes de publicar: `docker compose exec web python manage.py check --deploy`
23. ✅ Ao atualizar versão de imagem/binário, atualize **tag e digest/hash no mesmo commit**

### Sinais de Alerta - Quando Algo Está Errado

⚠️ **Atenção se:**

- Container `web` ou `worker` fica reiniciando constantemente
- `docker compose logs web` mostra `ModuleNotFoundError`
- Nginx retorna HTTP 502 mas o web responde na porta 8000
- Adicionou biblioteca ao projeto mas `requirements.txt` não foi atualizado
- Uma rota nova responde 500 com `TemplateDoesNotExist` mesmo com o template criado no disco
- `docker compose logs web` mostra `ImproperlyConfigured` — **esperado**: é um guardrail de segurança recusando configuração insegura (segredo ausente/inseguro, `DEBUG` com host não local, cookies/TLS desligados com `DEBUG=False`)
- `/accounts/login/` passa a responder `429` sob rajada — **esperado**: rate limiting ativo no nginx
- `/media/...` responde `404` — **esperado**: o location é `internal` por padrão
- Alguma credencial apareceu em documento, issue ou histórico do git — rotacione imediatamente e revise os logs de uso

**Ação imediata:**

```bash
# Verificar se pyproject.toml e requirements.txt estão sincronizados
uv sync

# Reexportar requirements.txt
uv lock
uv export --no-dev --no-hashes --output-file requirements.txt

# Rebuild tudo
docker compose up -d --build
docker compose restart nginx
docker compose restart web
```

---

## FLUXO OBRIGATÓRIO: Adicionar Dependências Python

**ATENÇÃO**: Esta seção é CRÍTICA. Erros na gestão de dependências causam falhas graves na aplicação.

### Ordem OBRIGATÓRIA de Operações

❌ **NUNCA faça isso**:

```bash
# ERRADO - Adicionar manualmente ao requirements.txt
echo "django-lib==1.0.0" >> requirements.txt

# ERRADO - Instalar apenas no venv local sem usar uv
pip install django-lib
```

✅ **SEMPRE faça isso**:

```bash
# PASSO 1: Adicionar via uv (atualiza pyproject.toml e uv.lock)
uv add "django-lib>=1.0.0"

# PASSO 2: Gerar lockfile e exportar para requirements.txt
uv lock
uv export --no-dev --no-hashes --output-file requirements.txt

# PASSO 3: Rebuild containers Docker (CRÍTICO!)
docker compose up -d --build

# PASSO 4: Reiniciar nginx (necessário após rebuild do web)
docker compose restart nginx

# PASSO 5: Verificar logs
docker compose logs web --tail 50
docker compose logs worker --tail 50

# PASSO 6: Testar endpoints
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/
```

### Por que essa ordem é CRÍTICA?

1. **pyproject.toml é a fonte da verdade**: Define as dependências do projeto
2. **uv.lock garante reprodutibilidade**: Lock exato das versões instaladas
3. **requirements.txt é um EXPORT**: Gerado automaticamente do pyproject.toml
4. **Docker usa requirements.txt no BUILD**: Alterações só surtem efeito com rebuild

### Erros Comuns e Soluções

#### Erro 1: "ModuleNotFoundError" no Docker

**Causa**: Biblioteca está no `requirements.txt` mas NÃO no `pyproject.toml`

**Solução**:

```bash
# Adicionar via uv
uv add "nome-lib>=versao"

# Reexportar requirements.txt
uv lock
uv export --no-dev --no-hashes --output-file requirements.txt

# Rebuild Docker
docker compose up -d --build
```

#### Erro 2: Biblioteca funciona localmente mas não no Docker

**Causa**: `requirements.txt` não foi atualizado ou Docker não foi rebuildado

**Solução**:

```bash
# Verificar se requirements.txt contém a biblioteca
grep nome-lib requirements.txt

# Se não contiver, exportar novamente
uv lock
uv export --no-dev --no-hashes --output-file requirements.txt

# Rebuild obrigatório
docker compose up -d --build
```

#### Erro 3: Nginx retorna HTTP 502 após rebuild

**Causa**: Nginx mantém cache de conexão para IP antigo do container web

**Solução**:

```bash
docker compose restart nginx
```

### Checklist para Adicionar Dependências

Use este checklist SEMPRE:

- [ ] **OBRIGATÓRIO**: Adicionar via `uv add "nome-lib>=versao"`
- [ ] **OBRIGATÓRIO**: Verificar se `pyproject.toml` foi atualizado
- [ ] **OBRIGATÓRIO**: Gerar lockfile via `uv lock`
- [ ] **OBRIGATÓRIO**: Exportar via `uv export --no-dev --no-hashes --output-file requirements.txt` (sem hashes; a fixação de versões é garantida pelo `uv.lock`)
- [ ] **OBRIGATÓRIO**: Verificar se `requirements.txt` contém a nova lib
- [ ] **OBRIGATÓRIO**: `docker compose up -d --build`
- [ ] **OBRIGATÓRIO**: `docker compose restart nginx`
- [ ] **OBRIGATÓRIO**: Verificar logs `docker compose logs web --tail 50`
- [ ] **OBRIGATÓRIO**: Testar endpoints `curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/`
- [ ] **OBRIGATÓRIO**: Executar check `docker compose exec web python manage.py check`

---

## Solução de Problemas

#### Erro: relation django_session does not exist

```bash
# As migrações não foram aplicadas. Execute:
docker compose exec web python manage.py migrate
```

#### Erro: HTTP 500 com TemplateDoesNotExist mesmo após criar o template

**Causa**: o Django 5.2 envolve os template loaders em `cached.Loader` **incondicionalmente** (`django/template/engine.py`), e o `cached.Loader` cacheia também as **ausências**. Se a rota foi acessada antes de o template existir, o processo do `runserver` continua respondendo 500 — mesmo com o arquivo no disco — até reiniciar.

**Diagnóstico** (o traceback mostra `TemplateDoesNotExist` e o postmortem aponta "Source does not exist" para um arquivo que existe):

```bash
docker compose logs web --tail 30
ls -la templates/registration/login.html
```

**Solução**:

```bash
docker compose restart web
```

#### Erro: `env file .env not found`

**Causa**: o `docker-compose.yml` usa `env_file: .env`, mas o arquivo não existe.

**Solução**:

```bash
cp .env.example .env
```

#### Erro: `Database is uninitialized and superuser password is not specified`

**Causa**: o serviço `db` recebeu `POSTGRES_PASSWORD` vazio — normalmente porque o bloco `DB_*` do `.env` está ausente ou comentado.

**Solução**: garanta que o `.env` contém o bloco ativo (seção [Configuração do Ambiente](#configuração-do-ambiente)) e recrie o serviço:

```bash
docker compose up -d --build db
```

#### Erro: `uv run pytest` falha com erro de coleta em `data/`

**Causa**: o pytest varre `./data/db` (datadir do PostgreSQL) — o `norecursedirs` do `pyproject.toml` não foi aplicado.

**Solução**: confira o `[tool.pytest.ini_options]` (seção Tailwind, passo 5) e rode novamente:

```bash
uv run pytest
```

#### Erro: arquivos gerados pelo container ficam com owner diferente do seu usuário no host (ex.: `root`, `nobody`)

**Causa**: os serviços `web`/`worker` executam com um usuário do container; `makemigrations` e `collectstatic` escrevem no bind mount `.:/code` e as tasks do Tailwind gravam `output.css` como o usuário que executa o binário (na execução de validação deste guia, o arquivo saiu como `nobody nogroup`).

**Diagnóstico**:

```bash
ls -la accounts/migrations core/static/core/css/output.css
```

**Solução** (Linux/macOS):

```bash
sudo chown -R "$USER":"$USER" accounts core staticfiles
```

**Solução alternativa** (executar como o seu usuário, apenas em Linux/macOS):

```bash
docker compose exec -u "$(id -u):$(id -g)" web python manage.py makemigrations
```

#### Erro: `/code` aparece vazio dentro do container (`can't open file '/code/manage.py'`) ou falha ao montar `nginx.conf` (`not a directory`)

**Causa**: o diretório do projeto está em um filesystem que o Docker **não** compartilha — por exemplo `tmpfs` (`/tmp` em muitos sistemas) ou uma pasta fora das pastas compartilhadas do Docker Desktop. Os bind mounts `.:/code` e `./nginx.conf` montam vazio ou falham. Comportamento observado em execução real: contêineres `web`/`worker` reiniciando com `can't open file '/code/manage.py'` e `nginx` falhando com `mount src=.../nginx.conf ... not a directory`.

**Diagnóstico**:

```bash
findmnt -no FSTYPE -T .
docker compose exec web ls -la /code
```

**Solução**: mova o projeto para um diretório em disco compartilhado com o Docker (ex.: dentro da sua pasta de projetos no home) e execute o fluxo novamente a partir dele.

#### Erro: nginx não inicia

```bash
# Verificar logs
docker compose logs nginx

# Rebuild nginx
docker compose up -d --build nginx
```

#### Erro: Tailwind CSS não está sendo aplicado nas páginas (sem estilo)

**Causa mais comum**: `STATICFILES_DIRS` não configurado no `settings.py`. O `collectstatic` não encontra os arquivos em `core/static/` e o Nginx retorna HTTP 404 para `output.css`.

**Diagnóstico**:

```bash
# Verificar se o CSS está acessível via Nginx
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/static/core/css/output.css
# Se retornar 404, verifique o STATICFILES_DIRS e o collectstatic

# Verificar se o arquivo existe no host e foi coletado
ls -la core/static/core/css/output.css
ls -la staticfiles/core/css/output.css
```

**Solução**:

1. Confirme o bloco no `core/settings.py` (já presente na versão completa da seção 7):

```python
STATICFILES_DIRS = [
    BASE_DIR / 'core' / 'static',
]
```

2. Recompile, colete e reinicie o nginx:

```bash
uv run task css-build
docker compose exec web python manage.py collectstatic --noinput
docker compose restart nginx
```

#### Erro: Porta 8080, 8000 ou 5432 já em uso

```bash
# Verificar o que está usando as portas
sudo lsof -i :8080
sudo lsof -i :8000
sudo lsof -i :5432
```

Pare o serviço que está usando a porta (se for outro projeto Docker: `docker compose stop` nele) ou remova o mapeamento correspondente no `docker-compose.yml`.

#### Erro: `the input device is not a TTY` em `docker compose exec`

**Causa**: execução sem terminal interativo (CI, scripts, redirecionamento).

**Solução**: acrescente `-T`:

```bash
docker compose exec -T web python manage.py migrate
```

#### Erro: `ImproperlyConfigured: SECRET_KEY ausente ou insegura`

**Causa**: o `settings.py` **recusa** subir sem segredo válido — é o comportamento correto (guarda contra chave pública/default).

**Solução**: gere e grave a chave no `.env` (passo 2 da seção [Configuração do Ambiente](#configuração-do-ambiente)):

```bash
uv run python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

⚠️ Não "resolva" colocando um valor literal no `settings.py` ou no `.env.example`.

#### Erro: `ImproperlyConfigured: ALLOWED_HOSTS nao pode conter '*'` ou `DEBUG=True so e permitido com hosts locais`

**Causa**: `ALLOWED_HOSTS='*'` ou `DEBUG=True` com host alcançável pela rede — combinação que expõe tracebacks e habilita Host header poisoning.

**Solução**: liste hosts explícitos e desligue `DEBUG` fora do local:

```bash
# .env
ALLOWED_HOSTS='localhost,127.0.0.1,seu-dominio'
DEBUG=False
```

#### Erro: `ImproperlyConfigured: Com DEBUG=False e obrigatorio definir SESSION_COOKIE_SECURE=True...`

**Causa**: modo produção (`DEBUG=False`) sem as flags de cookie/TLS — sessão e CSRF trafegariam em claro.

**Solução**: no `.env`, com HTTPS na frente:

```bash
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
```

#### Erro: `sha256sum: WARNING: 1 computed checksum did NOT match` no build da imagem

**Causa**: o binário baixado não corresponde ao hash fixado — versão diferente, CDN comprometida ou download corrompido.

**Solução**: **não remova** a verificação. Baixe novamente, confira a versão da release e, se a mudança for intencional, atualize o hash no `Dockerfile` de forma consciente:

```bash
curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/download/v4.1.18/tailwindcss-linux-x64
sha256sum tailwindcss-linux-x64
```

#### Erro: `429 Too Many Requests` ao testar `/accounts/login/` (ou `/admin/login/`)

**Causa**: rate limiting do nginx ativo (`20r/m`, `burst=5`) — proteção contra força bruta. Esperado em teste de rajada.

**Solução**: se o limite for apertado demais para o uso real, ajuste `rate`/`burst` em `nginx.conf` e recarregue:

```bash
docker compose restart nginx
```

Em produção, atrás de balanceador, configure `set_real_ip_from`/`real_ip_header` para limitar por IP real do cliente (senão todos compartilham o mesmo balde).

#### Erro: `403`/`404` ao acessar arquivo em `/media/`

**Causa**: `/media/` é `internal` no nginx — acesso direto por URL é bloqueado por projeto.

**Solução**: quando houver upload, sirva por uma view autenticada que valide a posse do arquivo e devolva `X-Accel-Redirect` para o location interno. Não torne `/media/` público.

---

## Referências

- [Documentação do Django](https://docs.djangoproject.com/en/5.2/)
- [Documentação do uv](https://docs.astral.sh/uv/)
- [Documentação do Docker Compose](https://docs.docker.com/compose/)
- [Documentação do Celery](https://docs.celeryproject.org/)
- [Modelo de Usuário Customizado](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/)
- [Tailwind CSS v4 Standalone CLI](https://tailwindcss.com/docs/installation/tailwind-cli)
- [django-htmx](https://django-htmx.readthedocs.io/)
- [pytest-django](https://pytest-django.readthedocs.io/)

---

**Última Atualização**: 2026-10-16
**Versão do Guia**: 0.6.0
**Versão Django**: 5.2.x (LTS)
**Versão Python**: 3.13
**Versão HTMX**: 2.0.9
**Versão Tailwind CSS**: 4.1.18
**Estado**: Fonte única (arquivos em estado final + runbook FASE 1–4), endurecido com as mitigações da auditoria de segurança de 2026-09-13 (F-01 a F-13, exceto o `pip install --require-hashes` do F-13, removido intencionalmente em 2026-10-06 — export do `requirements.txt` sem hashes) e validado por execução integral do fluxo em diretório limpo.

**Histórico de revisões**:

| Versão | Data | Mudanças |
|---|---|---|
| 0.6.0 | 2026-10-16 | 1. Páginas de erro customizadas do Nginx ativadas (`error_page` 400/401/402→400.html, 403, 404, 500/502/503/504→500.html) com `proxy_intercept_errors on` e `location /errors/` interno; HTML autônomos em `core/static/errors/`, entregues ao nginx pelo `collectstatic` (bind mount `staticfiles/errors:/etc/nginx/errors`). 2. Listing do `nginx.conf` sincronizado com o arquivo real (`Host $http_host` com preservação de porta nos dois `location` de proxy). 3. Banner de versão do topo removido — o rodapé + histórico de revisões volta a ser a única marcação de versão do documento. |
| 0.5.0 | 2026-10-08 | 1. `BaseModel` deixa de herdar `SoftDeleteMixin`: inclui apenas `TimestampMixin` — soft delete passa a ser **opt-in**, com nota de uso na seção 4.2; o mixin continua definido em `mixins.py` e exportado por `__init__.py`. 2. Docstring do `BaseModel` ajustada para "timestamp de criação/atualização". Projeto de referência atualizado em conjunto (verificado com `manage.py check` e `makemigrations --check`). |
| 0.4.0 | 2026-10-06 | 1. `requirements.txt` exportado **sem hashes** (`uv export --no-dev --no-hashes`) e `Dockerfile` instala com `pip install` simples (sem `--require-hashes`) — exceção intencional ao F-13; fixação de versões via `uv.lock`. 2. Removida a criação do script `docker-compose-dev.sh` e proibido criar *wrappers* do Docker Compose (Regra 2); FASE 3 usa `docker compose` direto. 3. Diretório `scripts/` só é criado no fluxo opcional de build local do Tailwind (passo 6 da seção 9). |
| 0.3.0 | 2026-09-13 | Endurecimento com as mitigações da auditoria de segurança (F-01 a F-13); execução validada integralmente em diretório limpo. |

**Segurança (rastreabilidade da auditoria de 2026-09-13)**:

| Achado | Mitigação neste guia |
|---|---|
| F-01 superusuário com senha default documentada | senha aleatória forte gerada em runtime (`.superuser-password`, modo 600, apagada ao final) — nenhuma senha fixa no documento |
| F-02 Postgres com credenciais default e porta aberta | `DB_PASS` gerado por máquina, `.env.example` sem valor utilizável, porta publicada apenas em `127.0.0.1` |
| F-03 `SECRET_KEY` com fallback/placeholder | `SECRET_KEY` sem fallback, validação de startup que recusa ausência/placeholder |
| F-04 `DEBUG=True` e `ALLOWED_HOSTS='*'` | defaults invertidos (`DEBUG` default `False`), `*` proibido, `DEBUG=True` só com hosts locais ou redes privadas/VPN, `8080` (Nginx) em todas as interfaces e demais portas em loopback |
| F-05 variáveis órfãs de credencial | `.env.example` contém apenas variáveis consumidas pelo projeto |
| F-06 `.env` legível por outros usuários | `chmod 600 .env` (com alternativa `icacls` no Windows) |
| F-07 `django_extensions`/`runserver` no runtime | `django-extensions` só no grupo dev e fora do `INSTALLED_APPS`; `runserver` marcado como desenvolvimento |
| F-08 download sem verificação de integridade | `sha256sum -c` do binário do Tailwind fixado por hash |
| F-09 link de admin exibido para não-staff | `{% if user.is_staff %}` no `home.html` |
| F-10 htmx `allowEval` + ausência de CSP | `<meta name="htmx-config" content='{"allowEval": false}'>`; CSP documentada (exige nonce) |
| F-11 sem rate limiting em autenticação | `limit_req_zone`/`limit_req` no nginx para login, reset de senha e admin (429) |
| F-12 transporte/cookies sem flags | `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, HSTS por ambiente, exigidos quando `DEBUG=False` |
| F-13 mídia pública, tags mutáveis, pip sem hashes | `/media/` `internal`, imagens por digest, Redis com senha (mitigação `pip install --require-hashes` removida intencionalmente em 2026-10-06: export sem hashes, fixação via `uv.lock`) |
