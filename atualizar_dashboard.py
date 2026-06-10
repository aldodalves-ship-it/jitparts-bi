"""Executa a rotina diaria completa de atualizacao do dashboard ecommerce."""

from __future__ import annotations

import subprocess
import sys
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter


ROOT_DIR = Path(__file__).resolve().parent
LOGS_DIR = ROOT_DIR / "logs"
LOG_PATH = LOGS_DIR / "ultima_execucao.log"
DEFAULT_TIMEOUT_SECONDS = 60 * 30
SUCCESS_LABEL = "[OK]"
WARNING_LABEL = "[AVISO]"
ERROR_LABEL = "[ERRO]"


@dataclass(frozen=True)
class PipelineStep:
    """Representa uma etapa executavel do pipeline diario."""

    name: str
    command: list[str]
    expected_outputs: tuple[Path, ...] = ()
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS


@dataclass
class StepResult:
    """Resultado consolidado de uma etapa."""

    step: PipelineStep
    success: bool
    duration_seconds: float
    return_code: int | None
    error: str | None = None


PIPELINE_STEPS = [
    PipelineStep(
        "Atualizar pedidos Mercado Livre",
        [sys.executable, "teste_ml_orders.py"],
        (Path("data/ml_orders.csv"),),
    ),
    PipelineStep(
        "Atualizar shipments/frete",
        [sys.executable, "teste_ml_shipments.py"],
        (Path("data/ml_shipments.csv"),),
    ),
    PipelineStep(
        "Atualizar lista de anuncios",
        [sys.executable, "teste_ml_items.py"],
        (Path("data/ml_items.csv"),),
    ),
    PipelineStep(
        "Atualizar detalhes/estoque dos anuncios",
        [sys.executable, "teste_ml_item_details.py"],
        (Path("data/ml_items_details.csv"),),
    ),
    PipelineStep(
        "Atualizar campanhas Ads",
        [sys.executable, "teste_ml_ads_campaigns.py"],
        (Path("data/ml_ads_campaigns.csv"),),
    ),
    PipelineStep(
        "Atualizar metricas Ads",
        [sys.executable, "teste_ml_ads_metrics.py"],
        (Path("data/ml_ads_metrics.csv"),),
    ),
    PipelineStep(
        "Atualizar base final consolidada",
        [sys.executable, "merge_ml_seconds.py", "data/seconds_cmv.xlsx"],
        (Path("data/dashboard_base_final.csv"),),
    ),
    PipelineStep(
        "Salvar historico DuckDB",
        [sys.executable, "salvar_historico_duckdb.py"],
        (Path("data/jitparts.duckdb"),),
    ),
]


def timestamp() -> str:
    """Retorna timestamp legivel para logs."""

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_duration(seconds: float) -> str:
    """Formata duracao em segundos/minutos."""

    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes, remainder = divmod(seconds, 60)
    return f"{int(minutes)}m {remainder:.2f}s"


def safe_text(text: object) -> str:
    """Normaliza texto para evitar falhas de encoding no Windows PowerShell."""

    return str(text).encode("utf-8", errors="replace").decode("utf-8", errors="replace")


def console_safe_text(text: str) -> str:
    """Adapta texto para o encoding do console sem quebrar o pipeline."""

    encoding = sys.stdout.encoding or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


def write_log_line(handle, message: str = "") -> None:
    """Escreve no terminal e no arquivo de log."""

    line = safe_text(f"[{timestamp()}] {message}" if message else "")
    print(console_safe_text(line))
    handle.write(f"{line}\n")
    handle.flush()


def output_status(path: Path) -> str:
    """Resume existencia e horario de atualizacao de um arquivo."""

    absolute_path = ROOT_DIR / path
    if not absolute_path.exists():
        return f"{path} (nao encontrado)"

    modified = datetime.fromtimestamp(absolute_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    return f"{path} (atualizado em {modified})"


def run_step(step: PipelineStep, log_handle) -> StepResult:
    """Executa uma etapa com captura de saida e timeout."""

    write_log_line(log_handle)
    write_log_line(log_handle, "=" * 88)
    write_log_line(log_handle, f"ETAPA: {step.name}")
    write_log_line(log_handle, "=" * 88)
    write_log_line(log_handle, f"Comando: {' '.join(step.command)}")

    start = perf_counter()
    try:
        child_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        completed = subprocess.run(
            step.command,
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=child_env,
            timeout=step.timeout_seconds,
            check=False,
        )
        duration = perf_counter() - start

        if completed.stdout:
            write_log_line(log_handle, "Saida stdout:")
            for line in completed.stdout.rstrip().splitlines():
                write_log_line(log_handle, line)
        if completed.stderr:
            write_log_line(log_handle, "Saida stderr:")
            for line in completed.stderr.rstrip().splitlines():
                write_log_line(log_handle, line)

        success = completed.returncode == 0
        symbol = SUCCESS_LABEL if success else ERROR_LABEL
        status = "sucesso" if success else f"falha (codigo {completed.returncode})"
        write_log_line(log_handle, f"{symbol} {step.name}: {status} em {format_duration(duration)}")
        return StepResult(
            step=step,
            success=success,
            duration_seconds=duration,
            return_code=completed.returncode,
            error=None if success else f"Codigo de retorno {completed.returncode}",
        )

    except subprocess.TimeoutExpired:
        duration = perf_counter() - start
        message = f"Timeout apos {step.timeout_seconds} segundos"
        write_log_line(log_handle, f"{ERROR_LABEL} {step.name}: {message}")
        return StepResult(
            step=step,
            success=False,
            duration_seconds=duration,
            return_code=None,
            error=message,
        )
    except Exception as exc:
        duration = perf_counter() - start
        message = f"Erro inesperado: {exc}"
        write_log_line(log_handle, f"{ERROR_LABEL} {step.name}: {message}")
        return StepResult(
            step=step,
            success=False,
            duration_seconds=duration,
            return_code=None,
            error=message,
        )


def print_final_summary(results: list[StepResult], total_seconds: float, log_handle) -> None:
    """Imprime resumo final consolidado."""

    successes = [result for result in results if result.success]
    failures = [result for result in results if not result.success]

    write_log_line(log_handle)
    write_log_line(log_handle, "#" * 88)
    write_log_line(log_handle, "RESUMO FINAL DA ATUALIZACAO")
    write_log_line(log_handle, "#" * 88)
    write_log_line(log_handle, f"Tempo total: {format_duration(total_seconds)}")
    write_log_line(log_handle, f"Etapas com sucesso: {len(successes)}")
    write_log_line(log_handle, f"Etapas com erro: {len(failures)}")

    if successes:
        write_log_line(log_handle, f"\n{SUCCESS_LABEL} Etapas concluidas:")
        for result in successes:
            write_log_line(log_handle, f"- {result.step.name} ({format_duration(result.duration_seconds)})")

    if failures:
        write_log_line(log_handle, f"\n{ERROR_LABEL} Etapas com erro:")
        for result in failures:
            detail = result.error or "Falha sem detalhe"
            write_log_line(log_handle, f"- {result.step.name}: {detail}")
    else:
        write_log_line(log_handle, f"\n{SUCCESS_LABEL} Nenhuma etapa falhou.")

    write_log_line(log_handle, f"\n{WARNING_LABEL} Arquivos atualizados/esperados:")
    seen_paths: set[Path] = set()
    for result in results:
        for path in result.step.expected_outputs:
            if path in seen_paths:
                continue
            seen_paths.add(path)
            write_log_line(log_handle, f"- {output_status(path)}")


def main() -> None:
    """Executa a rotina diaria inteira sem abrir o Streamlit."""

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    pipeline_start = perf_counter()

    with LOG_PATH.open("w", encoding="utf-8", errors="replace") as log_handle:
        write_log_line(log_handle, "#" * 88)
        write_log_line(log_handle, "INICIO DA ATUALIZACAO DIARIA DO DASHBOARD")
        write_log_line(log_handle, "#" * 88)

        results = [run_step(step, log_handle) for step in PIPELINE_STEPS]
        total_seconds = perf_counter() - pipeline_start
        print_final_summary(results, total_seconds, log_handle)
        write_log_line(log_handle, f"\nLog salvo em: {LOG_PATH.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    main()
