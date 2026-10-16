"""Task pós-cópia do Copier: personaliza a identidade do projeto gerado.

Arquitetura "espelho + task": o conteúdo chega byte-a-byte e a personalização
acontece aqui. A marca de exibição NÃO é replace — os templates leem
``{{ site_name }}`` em runtime (context processor + settings.SITE_NAME), e o
task só preenche ``SITE_NAME`` no .env/.env.example. Replace textual resta
para o técnico: slug no pyproject e na network do Compose.

Idempotente por construção — seguro no `copier update`: o replace é no-op na
segunda rodada (a string-fonte sumiu), `.env` e `git init` só quando
ausentes, `authors` só é inserido uma vez.
"""

import argparse
import datetime
import secrets
import subprocess
from pathlib import Path

BASE_NAME = 'django-setup-copier'
BASE_NETWORK = f'{BASE_NAME}_network'
BASE_PYPROJECT_NAME = f'name = "{BASE_NAME}"'
PLACEHOLDER_DESCRIPTION = 'Add your description here'
README_DATE_MARKER = '__DATA_GERACAO__'
BASE_SITE_NAME = f'SITE_NAME={BASE_NAME}'


def replace_in(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding='utf-8')
    if old in text:
        path.write_text(text.replace(old, new), encoding='utf-8')


def fix_env_example(root: Path, name: str) -> None:
    """O exemplo documenta ESTE projeto: SITE_NAME de fábrica vira o nome dado."""
    replace_in(root / '.env.example', BASE_SITE_NAME, f'SITE_NAME={name}')


def add_authors(pyproject: Path, author: str, email: str) -> None:
    """Insere `authors` no [project], logo abaixo de `description` (uma vez)."""
    lines = pyproject.read_text(encoding='utf-8').splitlines(keepends=True)
    if any(line.lstrip().startswith('authors') for line in lines):
        return
    safe_author = author.replace('"', r'\"')
    entry = f'authors = [{{ name = "{safe_author}"'
    if email:
        entry += f', email = "{email}"'
    entry += ' }]\n'
    for i, line in enumerate(lines):
        if line.lstrip().startswith('description'):
            lines.insert(i + 1, entry)
            pyproject.write_text(''.join(lines), encoding='utf-8')
            return


def personalize_pyproject(root: Path, slug: str, description: str, author: str, email: str) -> None:
    pyproject = root / 'pyproject.toml'
    replace_in(pyproject, BASE_PYPROJECT_NAME, f'name = "{slug}"')
    replace_in(pyproject, PLACEHOLDER_DESCRIPTION, description or f'Projeto {slug}')
    add_authors(pyproject, author, email)


def personalize_compose(root: Path, slug: str) -> None:
    replace_in(root / 'docker-compose.yml', BASE_NETWORK, f'{slug}_network')


def personalize_settings(root: Path, name: str) -> None:
    """O default de SITE_NAME também vira o nome dado (fallback do .env ausente)."""
    safe_name = name.replace("'", r"\'")
    replace_in(root / 'core' / 'settings.py', f"default='{BASE_NAME}'", f"default='{safe_name}'")


def stamp_readme(root: Path) -> None:
    today = datetime.date.today().strftime('%d/%m/%Y')
    replace_in(root / 'README.md', README_DATE_MARKER, today)


def write_env(root: Path, name: str) -> None:
    """Gera o .env a partir do .env.example, preenchendo os 4 secrets.

    token_urlsafe não produz '$' (alfabeto A-Za-z0-9_-): os valores chegam
    inteiros tanto na interpolação do Compose quanto no python-decouple.
    DATABASE_URL e CELERY_BROKER_URL embutem as senhas geradas — os lados
    Django e Postgres/Redis do .env precisam casar. SITE_NAME preenche a
    marca em runtime: é ela que os templates leem via context processor.
    """
    env = root / '.env'
    if env.exists():
        return
    postgres = secrets.token_urlsafe(24)
    redis = secrets.token_urlsafe(24)
    replacements = {
        'SECRET_KEY=': 'SECRET_KEY=' + secrets.token_urlsafe(50),
        'POSTGRES_PASSWORD=': f'POSTGRES_PASSWORD={postgres}',
        'REDIS_PASSWORD=': f'REDIS_PASSWORD={redis}',
        'DATABASE_URL=': f'DATABASE_URL=postgres://postgres:{postgres}@db:5432/postgres',
        'CELERY_BROKER_URL=': f'CELERY_BROKER_URL=redis://:{redis}@redis:6379/0',
        'SITE_NAME=': f'SITE_NAME={name}',
        '#APPS_SCRIPT_TOKEN=': 'APPS_SCRIPT_TOKEN=' + secrets.token_urlsafe(32),
    }
    lines = (root / '.env.example').read_text(encoding='utf-8').splitlines(keepends=True)
    filled = []
    for line in lines:
        for prefix, new_line in replacements.items():
            # startswith no linha crua: comentários ("# SECRET_KEY ...") não casam.
            if line.startswith(prefix):
                line = new_line + '\n'
                break
        filled.append(line)
    env.write_text(''.join(filled), encoding='utf-8')


def git_init(root: Path) -> None:
    if (root / '.git').exists():
        return
    subprocess.run(['git', 'init'], cwd=root, check=True, capture_output=True)


def main() -> None:
    parser = argparse.ArgumentParser(description='Personaliza o projeto gerado pelo template.')
    parser.add_argument('--name', required=True, help='Nome de exibição')
    parser.add_argument('--slug', required=True, help='Identificador técnico')
    parser.add_argument('--description', default='', help='Descrição de uma linha')
    parser.add_argument('--author', required=True, help='Nome do autor')
    parser.add_argument('--email', default='', help='E-mail do autor (opcional)')
    args = parser.parse_args()

    root = Path.cwd()

    personalize_pyproject(root, args.slug, args.description, args.author, args.email)
    personalize_compose(root, args.slug)
    personalize_settings(root, args.name)
    stamp_readme(root)
    fix_env_example(root, args.name)
    env_existed = (root / '.env').exists()
    git_existed = (root / '.git').exists()
    write_env(root, args.name)
    git_init(root)

    print(f'personalize: identidade aplicada ({args.name} / {args.slug})')
    print('personalize: .env ' + ('intocado — já existia' if env_existed else 'gerado com SECRET_KEY, POSTGRES_PASSWORD, REDIS_PASSWORD, APPS_SCRIPT_TOKEN e SITE_NAME'))
    print('personalize: git ' + ('intocado — já existia' if git_existed else 'inicializado (sem commit — o primeiro é seu)'))


if __name__ == '__main__':
    main()
