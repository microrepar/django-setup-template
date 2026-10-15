# django-setup-copier-template

Template [Copier](https://copier.readthedocs.io) que gera **cópias exatas** da base
[django-setup-copier](../) — Django 5.2 com autenticação por e-mail (ativação de cadastro
de uso único, reset de senha com gate de cota), Celery + Redis, Docker Compose
(Postgres, nginx com rate limit nos endpoints de auth, worker), HTMX + Tailwind e
settings fail-fast de segurança — com a **identidade personalizada** aplicada por tasks.

## Gerando um projeto

```console
$ copier copy --trust caminho/para/copier-template meu-projeto
```

Responda as 5 perguntas (nome, slug, descrição, autor, e-mail). O `--trust` autoriza
os tasks pós-cópia — em ordem:

1. **`scripts/personalize.py`** — marca nos templates HTML, slug no `pyproject.toml`
   e na network do Compose, `authors` + `description` no pyproject, README com data
   de geração, `.env` gerado do `.env.example` com `SECRET_KEY`,
   `POSTGRES_PASSWORD`, `REDIS_PASSWORD` e `APPS_SCRIPT_TOKEN` distintos (e
   `DATABASE_URL`/`CELERY_BROKER_URL` já compostos com as senhas), `git init`.
2. **`uv sync`** — `.venv` + `uv.lock` já com o nome novo do projeto.
3. **`uv export`** ×2 — `requirements.txt` e `requirements-dev.txt` frescos
   (mesmos comandos declarados nos cabeçalhos dos requirements do base).

Falha de `uv` (ausente ou sem rede) **não aborta** a geração: vira aviso, e o README
do projeto gerado documenta os comandos para rodar na mão.

Projetos gerados saem com `.copier-answers.yml` commitável — `copier update` recebe
as evoluções do template (diff 3-way entre tags deste repo).

## Manutenção (neste repo)

O projeto base (`../`) é a fonte da verdade. Ciclo de manutenção:

```console
$ uv run task sync          # base → template/ (exclusões de scripts/exclusions.py)
$ uv run task parity        # valida espelho + smoke de renderização
$ uv run task parity --full # pipeline completo: tasks + uv sync + manage.py check
$ uv run task lint
```

Depois: commit + tag (`vX.Y.Z`) — é das tags que o `copier update` diffa.

## Estrutura

- `template/` — espelho byte-a-byte do base (mais `.copier-answers.yml.jinja` e
  `README.md.jinja`, autorais). **Zero Jinja no conteúdo**: os templates Django do
  projeto viajam intactos; personalização é replace textual no task.
- `scripts/` — `personalize.py` (task pós-cópia), `sync.py`, `parity.py` e
  `exclusions.py` (lista única de exclusões, fonte comum de sync e parity).
- `copier.yml` — perguntas, tasks e configuração (`_subdirectory: template`).

## Exclusões do espelho

Artefatos de dev e segredos ficam fora: `db.sqlite3`, `data/`, `staticfiles/`,
`media/`, `.venv/`, caches, `uv.lock`, `requirements*.txt` (derivados — o task
regenera), `.env` (nunca), `.claude/`, `.ai-jail`, `README.md` (vazio no base),
`shared/utils.py` (vazio). **Mantém**: `.docs/` completo (guia + script `.gs`),
`.vscode/`, `CLAUDE.md`, `.env.example`.
