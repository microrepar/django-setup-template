"""Verifica o template de ponta a ponta, sem depender de nada externo.

Modo rápido (default): renderiza o template com `copier copy --skip-tasks`
em diretório temporário e valida o que o Copier faz sozinho (answers file,
README renderizado, conteúdo intacto, nenhum efeito colateral de task).

`--full`: deixa os tasks rodarem (personalize + uv sync + uv export) e valida
cada promessa do pipeline — identidade aplicada, .env com secrets, git init,
requirements gerados — terminando com `manage.py check` no projeto gerado.
"""

import datetime
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE_NAME = b'django-setup-copier'
NAME = 'Projeto Verificação'
SLUG = 'projeto-verificacao'


def make_src(tmp: Path) -> Path:
    """Cópia do working tree sem .git: o Copier renderiza o estado ATUAL.

    Num caminho local com repo git, o Copier usa o HEAD commitado — edições
    ainda não commitadas ficariam de fora da verificação. A cópia sem .git
    garante que o check valida exatamente o que está prestes a ser commitado.
    """
    src = tmp / 'src'
    shutil.copytree(
        REPO, src,
        ignore=shutil.ignore_patterns('.git', '.venv', '__pycache__', '.ruff_cache', '.pytest_cache'),
    )
    return src


def run_copier(src: Path, dst: Path, skip_tasks: bool) -> None:
    cmd = [
        'copier', 'copy', '--defaults', '--trust',
        '--data', f'project_name={NAME}',
        '--data', f'project_slug={SLUG}',
        '--data', 'project_description=Verificação do template',
        '--data', 'author_name=Verificação',
        '--data', 'author_email=verificacao@exemplo.test',
    ]
    if skip_tasks:
        cmd.append('--skip-tasks')
    cmd += [str(src), str(dst)]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'copier copy falhou:\n{result.stdout}\n{result.stderr}')


def leaked_traces(proj: Path) -> list[str]:
    """Rastros do nome de fábrica em qualquer arquivo do gerado.

    Isenções:
    - .copier-answers.yml registra o caminho do template — metadado do
      Copier, necessário ao `copier update`; não é conteúdo do projeto;
    - __pycache__ é bytecode derivado (embute caminhos absolutos da máquina
      que compilou — nunca conteúdo do projeto).
    """
    traces = []
    for path in proj.rglob('*'):
        if not path.is_file() or path.name == '.copier-answers.yml':
            continue
        if '__pycache__' in path.parts:
            continue
        if BASE_NAME in path.read_bytes():
            traces.append(f'rastro de fábrica em {path.relative_to(proj)}')
    return traces


def fast_checks(proj: Path) -> list[str]:
    """Render estrutural, sem tasks: conteúdo intacto, jinja renderizado."""
    errors = []
    if not (proj / '.copier-answers.yml').exists():
        errors.append('.copier-answers.yml ausente no gerado')
    readme = (proj / 'README.md').read_text(encoding='utf-8')
    if NAME not in readme:
        errors.append('README sem o nome do projeto (jinja não renderizou)')
    # Sem tasks, o marcador fica cru: quem carimba a data é o personalize.py.
    if '__DATA_GERACAO__' not in readme:
        errors.append('README sem o marcador de data (deveria estar cru, sem tasks)')
    # Sem tasks, nada deveria mudar: a marca de fábrica ainda está nos HTML.
    base_html = (proj / 'templates' / 'base.html').read_text(encoding='utf-8')
    if 'django-setup-copier' not in base_html:
        errors.append('base.html não está intacto (sem tasks, nada deveria mudar)')
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
    if 'authors = ' not in pyproject or 'Verificação' not in pyproject:
        errors.append('authors ausente no pyproject')
    compose = (proj / 'docker-compose.yml').read_text(encoding='utf-8')
    if f'{SLUG}_network' not in compose:
        errors.append('network não personalizada no compose')
    env = proj / '.env'
    if not env.exists():
        errors.append('.env não gerado')
    else:
        text = env.read_text(encoding='utf-8')
        wanted = (
            'SECRET_KEY=', 'POSTGRES_PASSWORD=', 'REDIS_PASSWORD=', 'APPS_SCRIPT_TOKEN=',
            'DATABASE_URL=postgres://postgres:', 'CELERY_BROKER_URL=redis://:',
        )
        for prefix in wanted:
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
    """manage.py check no gerado — settings, .env e apps de ponta a ponta."""
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
    with tempfile.TemporaryDirectory(prefix='copier-check-') as tmp:
        src = make_src(Path(tmp))
        proj = Path(tmp) / 'proj'
        try:
            run_copier(src, proj, skip_tasks=not full)
        except RuntimeError as error:
            print(f'✗ copier copy\n{error}')
            sys.exit(1)
        ok = report(
            'render ' + ('completo (tasks)' if full else 'estrutural (--skip-tasks)'),
            full_checks(proj) if full else fast_checks(proj),
        )
        if full:
            ok = report('manage.py check no gerado', manage_check(proj)) and ok
    if not ok:
        sys.exit(1)


if __name__ == '__main__':
    main()
