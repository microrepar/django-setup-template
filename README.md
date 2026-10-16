# django-setup-copier-template

Template [Copier](https://copier.readthedocs.io) de projeto Django pronto pra produção:

- **Autenticação por e-mail** — usuário custom sem username, cadastro com link
  de ativação de uso único (nonce no hash do token), login bloqueado até a
  verificação do e-mail, reset de senha com gate de capacidade da fila de envio
- **Celery + Redis** — e-mails fora da requisição HTTP, retries com backoff e
  modo eager sem broker (dev simples, sem fila)
- **Docker Compose** — Postgres, nginx (rate limit nos endpoints de
  autenticação, `/media/` bloqueado a acesso direto), worker com limites de
  recurso, imagens pinadas por digest
- **HTMX + Tailwind v4** (CLI dentro do container)
- **Settings fail-fast** — `SECRET_KEY` sem fallback, `DEBUG` só em rede
  privada/VPN, HTTPS e cookies `Secure` obrigatórios em produção

## Gerando um projeto

```console
$ copier copy --trust caminho/para/este/repo meu-projeto
```

Responda as 5 perguntas (nome, slug, descrição, autor, e-mail). O `--trust`
autoriza os tasks pós-cópia — em ordem:

1. **`scripts/personalize.py`** — marca nos templates HTML, slug no
   `pyproject.toml` e na network do Compose, `authors` + `description` no
   pyproject, data de criação no README, `.env` gerado do `.env.example` com
   `SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD` e `APPS_SCRIPT_TOKEN`
   distintos (e `DATABASE_URL`/`CELERY_BROKER_URL` já compostos com as senhas),
   `git init`.
2. **`uv sync`** — `.venv` + `uv.lock` já com o nome novo do projeto.
3. **`uv export`** ×2 — `requirements.txt` e `requirements-dev.txt` frescos.

Falha de `uv` (ausente ou sem rede) **não aborta** a geração: vira aviso, e o
README do projeto gerado documenta os comandos para rodar na mão.

Projetos gerados saem com `.copier-answers.yml` — `copier update` recebe as
evoluções deste template (diff 3-way entre tags).

## Verificação

```console
$ uv run task check        # render num diretório temporário + validações
$ uv run task check --full # pipeline completo: tasks + uv sync + manage.py check
$ uv run task lint         # ruff do tooling
```

## Estrutura

- `template/` — o conteúdo que o Copier gera (mais `.copier-answers.yml.jinja`
  e `README.md.jinja`, autorais). Zero Jinja no conteúdo: os templates Django
  viajam intactos; personalização é o task.
- `scripts/` — `personalize.py` (task pós-cópia) e `check.py` (verificação).
- `copier.yml` — perguntas, tasks e configuração (`_subdirectory: template`).
