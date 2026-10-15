"""Valida o template: espelho fiel ao base + renderização correta do Copier.

1. Espelho: template/ deve conter exatamente os arquivos do base (exclusões
   de exclusions.py aplicadas, byte-a-byte), mais os dois autorais
   (.copier-answers.yml.jinja e README.md.jinja).
2. Smoke rápido (default): `copier copy --skip-tasks` em diretório temporário
   e asserts estruturais no gerado — render ok, answers file presente,
   templates Django intactos, nenhum efeito colateral de task.
3. `--full`: copia SEM --skip-tasks e valida o pipeline inteiro (personalize,
   uv sync, uv export) + `manage.py check` no projeto gerado.
"""

import datetime
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from exclusions import TEMPLATE_ONLY, excluded

REPO = Path(__file__).resolve().parent.parent
BASE = REPO.parent
TEMPLATE = REPO / 'template'
BASE_NAME = b'django-setup-copier'
NAME = 'Projeto Paridade'
SLUG = 'projeto-paridade'


def walk_files(root: Path, skip: set[str] | None = None) -> list[str]:
    """Caminhos relativos (POSIX) dos arquivos sob root, sem os excluídos."""
    skip = skip or set()
    found: list[str] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError as error:
            print(f'AVISO: pulando {current}: {error.strerror}')
            continue
        for entry in entries:
            rel = entry.relative_to(root).as_posix()
            if rel in skip or excluded(rel):
                continue
            if entry.is_dir():
                stack.append(entry)
            else:
                found.append(rel)
    return found


def check_mirror() -> list[str]:
    errors = []
    src = set(walk_files(BASE))
    dst = set(walk_files(TEMPLATE, skip=TEMPLATE_ONLY))
    for rel in sorted(src - dst):
        errors.append(f'espelho sem o arquivo do base: {rel}')
    for rel in sorted(dst - src):
        errors.append(f'espelho com arquivo além do base: {rel}')
    for rel in sorted(src & dst):
        if (BASE / rel).read_bytes() != (TEMPLATE / rel).read_bytes():
            errors.append(f'conteúdo divergente: {rel}')
    return errors


def run_copier(dst: Path, skip_tasks: bool) -> None:
    cmd = [
        'copier', 'copy', '--defaults', '--trust',
        '--data', f'project_name={NAME}',
        '--data', f'project_slug={SLUG}',
        '--data', 'project_description=Verificação de paridade',
        '--data', 'author_name=Paridade',
        '--data', 'author_email=paridade@exemplo.test',
    ]
    if skip_tasks:
        cmd.append('--skip-tasks')
    cmd += [str(REPO), str(dst)]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'copier copy falhou:\n{result.stdout}\n{result.stderr}')


def leaked_traces(proj: Path) -> list[str]:
    """Rastros do nome do base em qualquer arquivo do gerado.

    Isenções deliberadas:
    - .copier-answers.yml registra o caminho do template (contém o nome do
      repo pai) — metadado do Copier, não conteúdo;
    - README.md declara a proveniência ("gerado a partir do template
      django-setup-copier em ...") — decisão de design, rastro intencional;
    - __pycache__ é bytecode derivado (embute caminhos absolutos da máquina
      que compilou — nunca conteúdo do projeto).
    """
    exempt_names = {'.copier-answers.yml', 'README.md'}
    traces = []
    for path in proj.rglob('*'):
        if not path.is_file() or path.name in exempt_names:
            continue
        if '__pycache__' in path.parts:
            continue
        if BASE_NAME in path.read_bytes():
            traces.append(f'rastro do base em {path.relative_to(proj)}')
    return traces


def fast_checks(proj: Path) -> list[str]:
    """Render estrutural, sem tasks: espelho intacto, jinja renderizado."""
    errors = []
    if not (proj / '.copier-answers.yml').exists():
        errors.append('.copier-answers.yml ausente no gerado')
    readme = (proj / 'README.md').read_text(encoding='utf-8')
    if NAME not in readme:
        errors.append('README sem o nome do projeto (jinja não renderizou)')
    # Sem tasks, o marcador fica cru: quem carimba a data é o personalize.py.
    if '__DATA_GERACAO__' not in readme:
        errors.append('README sem o marcador de data (deveria estar cru, sem tasks)')
    # Sem tasks, o espelho chega intacto: a marca do base ainda está nos HTML.
    base_html = (proj / 'templates' / 'base.html').read_text(encoding='utf-8')
    if 'django-setup-copier' not in base_html:
        errors.append('base.html não está byte-a-byte (sem tasks, nada deveria mudar)')
    if (proj / '.env').exists() or (proj / '.git').exists():
        errors.append('.env/.git presentes mesmo com --skip-tasks')
    return errors


def full_checks(proj: Path) -> list[str]:
    """Pipeline completo: identidade aplicada, secrets, bootstrap."""
    errors = leaked_traces(proj)
    base_html = (proj / 'templates' / 'base.html').read_text(encoding='utf-8')
    if NAME not in base_html:
        errors.append('nome de exibição ausente em templates/base.html')
    # Nota: no ano do snapshot (2026) esta checagem passa trivialmente — o
    # replace é no-op; ela passa a provar algo a partir de 2027.
    if f'&copy; {datetime.date.today().year}' not in base_html:
        errors.append('ano corrente ausente no rodapé do base.html')
    pyproject = (proj / 'pyproject.toml').read_text(encoding='utf-8')
    if f'name = "{SLUG}"' not in pyproject:
        errors.append('slug ausente no pyproject')
    if 'authors = ' not in pyproject or 'Paridade' not in pyproject:
        errors.append('authors ausente no pyproject')
    compose = (proj / 'docker-compose.yml').read_text(encoding='utf-8')
    if f'{SLUG}_network' not in compose:
        errors.append('network não personalizada no compose')
    env = (proj / '.env')
    if not env.exists():
        errors.append('.env não gerado')
    else:
        text = env.read_text(encoding='utf-8')
        for prefix in ('SECRET_KEY=', 'POSTGRES_PASSWORD=', 'REDIS_PASSWORD=', 'APPS_SCRIPT_TOKEN=', 'DATABASE_URL=postgres://postgres:', 'CELERY_BROKER_URL=redis://:'):
            if not any(line.startswith(prefix) and len(line) > len(prefix) for line in text.splitlines()):
                errors.append(f'.env sem valor preenchido: {prefix}...')
    if not (proj / '.git').exists():
        errors.append('git init não executado')
    for req in ('requirements.txt', 'requirements-dev.txt'):
        if not (proj / req).exists():
            errors.append(f'{req} não gerado pelo uv export')
    if '__DATA_GERACAO__' in (proj / 'README.md').read_text(encoding='utf-8'):
        errors.append('README sem a data de geração carimbada')
    return errors


def manage_check(proj: Path) -> list[str]:
    """manage.py check no gerado — valida settings, .env e apps de ponta a ponta."""
    result = subprocess.run(
        ['uv', 'run', 'python', 'manage.py', 'check'],
        check=False, cwd=proj, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return [f'manage.py check falhou:\n{result.stdout}\n{result.stderr}']
    return []


def report(section: str, errors: list[str]) -> bool:
    if errors:
        print(f'✗ {section}')
        for error in errors:
            print(f'    {error}')
        return False
    print(f'✓ {section}')
    return True


def main() -> None:
    full = '--full' in sys.argv
    ok = report('espelho × base', check_mirror())
    with tempfile.TemporaryDirectory(prefix='copier-parity-') as tmp:
        proj = Path(tmp) / 'proj'
        try:
            run_copier(proj, skip_tasks=not full)
        except RuntimeError as error:
            print(f'✗ copier copy\n{error}')
            sys.exit(1)
        ok = report('render ' + ('completo (tasks)' if full else 'estrutural (--skip-tasks)'),
                    full_checks(proj) if full else fast_checks(proj))
        if full:
            ok = report('manage.py check no gerado', manage_check(proj)) and ok
    if not ok:
        sys.exit(1)


if __name__ == '__main__':
    main()
