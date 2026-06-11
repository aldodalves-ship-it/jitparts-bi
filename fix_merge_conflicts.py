"""fix_merge_conflicts.py

Resolve conflitos de merge automaticamente em todos os arquivos .py,
mantendo SEMPRE a versao LOCAL (HEAD) e descartando a versao remota.

Uso:
    python fix_merge_conflicts.py          # processa todos os .py do diretorio
    python fix_merge_conflicts.py app.py   # processa apenas um arquivo

Logica por bloco de conflito:
        [codigo local — MANTIDO]
    
O resultado e o arquivo sem marcadores, apenas com o codigo local.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def resolve_conflicts_keep_head(text: str) -> tuple[str, int]:
    """Remove marcadores de conflito mantendo o bloco HEAD.

    Retorna (texto_limpo, quantidade_de_blocos_resolvidos).
    """
    # Padrao: <<< HEAD ... === ... >>> hash
    # re.DOTALL para capturar quebras de linha dentro do bloco
    pattern = re.compile(
        r"<<<<<<< .*?\n"   # marcador de inicio + nome da branch
        r"(.*?)"           # grupo 1: conteudo HEAD (MANTIDO)
        r"=======\n"       # separador
        r".*?"             # conteudo remoto (DESCARTADO)
        r">>>>>>> .*?\n",  # marcador de fim + hash
        re.DOTALL,
    )

    count = 0

    def _replace(m: re.Match) -> str:
        nonlocal count
        count += 1
        return m.group(1)  # retorna apenas o bloco HEAD

    cleaned = pattern.sub(_replace, text)
    return cleaned, count


def process_file(path: Path, dry_run: bool = False) -> tuple[bool, int]:
    """Processa um arquivo .py.

    Retorna (modificado, blocos_resolvidos).
    """
    try:
        original = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        original = path.read_text(encoding="utf-8", errors="replace")

    # Verificacao rapida antes de processar
    if "<<<<<<< " not in original:
        return False, 0

    cleaned, count = resolve_conflicts_keep_head(original)

    if count == 0:
        return False, 0

    if not dry_run:
        path.write_text(cleaned, encoding="utf-8")

    return True, count


def find_py_files(root: Path) -> list[Path]:
    """Encontra todos os .py excluindo venvs e caches."""
    exclude_dirs = {".venv", "venv", "env", "__pycache__", ".git", "node_modules"}
    files = []
    for f in root.rglob("*.py"):
        if not any(part in exclude_dirs for part in f.parts):
            files.append(f)
    return sorted(files)


def main() -> None:
    root = Path(__file__).resolve().parent

    # Se argumentos passados, processar apenas esses arquivos
    if len(sys.argv) > 1:
        targets = [Path(a) for a in sys.argv[1:]]
    else:
        targets = find_py_files(root)

    print(f"Verificando {len(targets)} arquivo(s)...\n")

    total_files = 0
    total_blocks = 0

    for path in targets:
        modified, count = process_file(path)
        if modified:
            total_files += 1
            total_blocks += count
            print(f"  RESOLVIDO  {path.name}  ({count} bloco(s) de conflito)")

    print()
    if total_files == 0:
        print("Nenhum conflito encontrado. Projeto limpo.")
    else:
        print(f"Resumo: {total_files} arquivo(s) corrigido(s), {total_blocks} bloco(s) resolvido(s).")

    # Validacao de sintaxe nos arquivos modificados
    if total_files > 0:
        print("\nValidando sintaxe...")
        import py_compile, traceback

        all_ok = True
        for path in targets:
            # Reprocessar apenas os que foram tocados
            if not path.read_text(encoding="utf-8", errors="replace").__contains__("<<<<<<<"):
                try:
                    py_compile.compile(str(path), doraise=True)
                    print(f"  OK        {path.name}")
                except py_compile.PyCompileError as e:
                    print(f"  ERRO      {path.name}: {e}")
                    all_ok = False

        print()
        if all_ok:
            print("Todos os arquivos validados com sucesso.")
        else:
            print("ATENCAO: Alguns arquivos ainda tem erros de sintaxe. Revise manualmente.")


if __name__ == "__main__":
    main()
