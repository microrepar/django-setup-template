"""Sincroniza o projeto base para dentro de template/ (base → espelho).

O base é a fonte da verdade: features novas entram lá e chegam ao template
por este comando. A cópia aplica as exclusões de exclusions.py, preserva os
dois arquivos autorais do espelho (.copier-answers.yml.jinja e README.md.jinja)
e remove de template/ o que deixou de existir no base.
"""

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from exclusions import TEMPLATE_ONLY, excluded

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = REPO / 'template'


def walk_source(base: Path) -> list[str]:
    """Caminhos relativos (POSIX) dos arquivos do base, sem as exclusões."""
    found: list[str] = []
    stack = [base]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError as error:
            # ex.: data/db é root-owned — não pode parar o sync
            print(f'  (pulando {current}: {error.strerror})')
            continue
        for entry in entries:
            rel = entry.relative_to(base).as_posix()
            if excluded(rel):
                continue
            if entry.is_dir():
                stack.append(entry)
            else:
                found.append(rel)
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description='Copia o base para template/.')
    parser.add_argument(
        '--base',
        type=Path,
        default=REPO.parent,
        help='Raiz do projeto base (default: o diretório acima deste repo)',
    )
    args = parser.parse_args()
    base: Path = args.base

    if not (base / 'manage.py').exists():
        sys.exit(f'Base inválido: {base} não contém manage.py')

    copied = 0
    for rel in walk_source(base):
        dest = TEMPLATE / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(base / rel, dest)
        copied += 1
    print(f'sync: {copied} arquivo(s) copiado(s) de {base}')

    # Remove do espelho o que saiu do base (ou que uma exclusão nova cobriu),
    # preservando os autorais. rglob reverso = filhos antes dos pais.
    removed = 0
    for path in sorted(TEMPLATE.rglob('*'), reverse=True):
        rel = path.relative_to(TEMPLATE).as_posix()
        if rel in TEMPLATE_ONLY:
            continue
        if not (base / rel).exists() or excluded(rel):
            if path.is_file():
                path.unlink()
                removed += 1
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()
    print(f'sync: {removed} arquivo(s) removido(s) de template/')


if __name__ == '__main__':
    main()
