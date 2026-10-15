"""Exclusões do espelho — fonte única de verdade para sync e parity.

O que sai da cópia base → template/: artefatos de dev gerados localmente,
segredos, lixo de cache e arquivos que o task de personalização recria no
projeto gerado (requirements são derivados do pyproject via uv export; o
README nasce do README.md.jinja; o uv.lock nasce no uv sync).

O que NÃO pode faltar no espelho: .docs/ completo (guia + script .gs),
.vscode/, CLAUDE.md do base, .env.example, Dockerfile, compose, nginx.conf.
"""

from pathlib import PurePosixPath

# Nomes de diretório excluídos em QUALQUER profundidade. O bytecode de cache
# embute o caminho absoluto da máquina que o compilou — nunca deve viajar.
EXCLUDE_DIR_NAMES = {'__pycache__'}

# Caminhos relativos à raiz do base, em notação POSIX.
EXCLUDE_PATHS = {
    '.ai-jail',
    '.claude',  # settings locais da sessão — não é conteúdo do projeto
    '.env',  # segredo real — nunca viaja
    '.git',  # histórico do base
    '.pytest_cache',
    '.ruff_cache',
    '.venv',
    'copier-template',  # este repo: o espelho não se copia dentro de si
    'data',  # volume do Postgres (root-owned no dev)
    'db.sqlite3',
    'media',
    'README.md',  # vazio no base; o gerado nasce de README.md.jinja
    'requirements-dev.txt',  # derivado: uv export no task pós-cópia
    'requirements.txt',  # idem
    'shared/utils.py',  # arquivo vazio, morto
    'staticfiles',
    'uv.lock',  # derivado: nasce no uv sync do projeto gerado
}

# Arquivos que existem SÓ no template (autorais, não vêm do base).
TEMPLATE_ONLY = {
    '.copier-answers.yml.jinja',
    'README.md.jinja',
}


def excluded(rel: str) -> bool:
    """True se o caminho relativo (POSIX) do base fica fora do espelho.

    Casa nomes de diretório em qualquer profundidade (ex.: accounts/__pycache__)
    e caminhos a partir da raiz (ex.: data, .claude) com todos os seus descendentes.
    """
    parts = PurePosixPath(rel).parts
    if any(part in EXCLUDE_DIR_NAMES for part in parts):
        return True
    return any('/'.join(parts[:i]) in EXCLUDE_PATHS for i in range(1, len(parts) + 1))
