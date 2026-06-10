"""Salva snapshots historicos das principais bases do dashboard em DuckDB."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd


DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "jitparts.duckdb"


@dataclass(frozen=True)
class SnapshotSource:
    """Mapeia um CSV de origem para sua tabela historica."""

    csv_path: Path
    table_name: str


SNAPSHOT_SOURCES = [
    SnapshotSource(DATA_DIR / "dashboard_base_final.csv", "historico_vendas"),
    SnapshotSource(DATA_DIR / "ml_ads_metrics.csv", "historico_ads"),
    SnapshotSource(DATA_DIR / "ml_items_details.csv", "historico_estoque"),
    SnapshotSource(DATA_DIR / "ml_shipments.csv", "historico_fretes"),
    SnapshotSource(DATA_DIR / "ml_orders.csv", "historico_pedidos"),
]


def log(message: str) -> None:
    """Imprime mensagens claras no terminal."""

    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}")


def ensure_control_table(con: duckdb.DuckDBPyConnection) -> None:
    """Cria tabela de controle de execucoes se ainda nao existir."""

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS controle_execucoes (
            data_snapshot TIMESTAMP,
            tabela VARCHAR,
            linhas_inseridas BIGINT,
            status VARCHAR,
            mensagem VARCHAR
        )
        """
    )


def append_control_row(
    con: duckdb.DuckDBPyConnection,
    snapshot_at: datetime,
    table_name: str,
    rows_inserted: int,
    status: str,
    message: str,
) -> None:
    """Registra o resultado de uma etapa na tabela de controle."""

    con.execute(
        """
        INSERT INTO controle_execucoes (
            data_snapshot,
            tabela,
            linhas_inseridas,
            status,
            mensagem
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        [snapshot_at, table_name, rows_inserted, status, message],
    )


def prepare_snapshot_df(csv_path: Path, snapshot_at: datetime) -> pd.DataFrame:
    """Le CSV e adiciona data_snapshot."""

    df = pd.read_csv(csv_path)
    df = deduplicate_duckdb_columns(df)
    df["data_snapshot"] = snapshot_at
    return df


def deduplicate_duckdb_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Evita colisao case-insensitive de colunas no DuckDB."""

    renamed = df.copy()
    seen: set[str] = set()
    new_columns: list[str] = []

    for column in renamed.columns.astype(str):
        candidate = column
        base = column
        suffix = 2
        while candidate.lower() in seen:
            candidate = f"{base}_dup{suffix}"
            suffix += 1
        seen.add(candidate.lower())
        new_columns.append(candidate)

    renamed.columns = new_columns
    return renamed


def quote_identifier(identifier: str) -> str:
    """Escapa identificadores para uso seguro em SQL DuckDB."""

    return '"' + identifier.replace('"', '""') + '"'


def align_snapshot_schema(
    con: duckdb.DuckDBPyConnection,
    table_name: str,
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Alinha o DataFrame ao schema historico, aceitando novas colunas."""

    con.register("snapshot_schema_df", df)
    try:
        snapshot_schema = con.execute("DESCRIBE SELECT * FROM snapshot_schema_df").df()
    finally:
        con.unregister("snapshot_schema_df")

    table_schema = con.execute(f"DESCRIBE {quote_identifier(table_name)}").df()
    existing_columns = table_schema["column_name"].tolist()
    existing_by_lower = {column.lower(): column for column in existing_columns}

    canonicalized = df.copy()
    rename_map = {
        column: existing_by_lower[column.lower()]
        for column in canonicalized.columns
        if column.lower() in existing_by_lower and column != existing_by_lower[column.lower()]
    }
    if rename_map:
        canonicalized = canonicalized.rename(columns=rename_map)

    existing_set = set(existing_columns)
    existing_lower_set = set(existing_by_lower)

    for row in snapshot_schema.itertuples(index=False):
        if row.column_name.lower() in existing_lower_set:
            continue
        con.execute(
            f"ALTER TABLE {quote_identifier(table_name)} "
            f"ADD COLUMN {quote_identifier(row.column_name)} {row.column_type}"
        )
        existing_columns.append(row.column_name)
        existing_set.add(row.column_name)
        existing_lower_set.add(row.column_name.lower())

    aligned = canonicalized.copy()
    for column in existing_columns:
        if column not in aligned.columns:
            aligned[column] = pd.NA
    return aligned[existing_columns]


def keep_latest_snapshot_per_day(con: duckdb.DuckDBPyConnection, table_name: str) -> None:
    """Mantem apenas o snapshot mais recente de cada dia calendario."""

    con.execute(
        f"""
        DELETE FROM {quote_identifier(table_name)}
        WHERE data_snapshot NOT IN (
            SELECT MAX(data_snapshot)
            FROM {quote_identifier(table_name)}
            GROUP BY CAST(data_snapshot AS DATE)
        )
        """
    )


def append_snapshot(
    con: duckdb.DuckDBPyConnection,
    source: SnapshotSource,
    snapshot_at: datetime,
) -> tuple[int, str, str]:
    """Insere um snapshot em sua tabela historica, preservando historico anterior."""

    if not source.csv_path.exists():
        return 0, "aviso", f"Arquivo ausente: {source.csv_path}"

    try:
        df = prepare_snapshot_df(source.csv_path, snapshot_at)
    except Exception as exc:
        return 0, "erro", f"Falha ao ler CSV {source.csv_path}: {exc}"

    if df.empty:
        return 0, "aviso", f"Arquivo vazio: {source.csv_path}"

    try:
        table_exists = con.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = ?
            """,
            [source.table_name],
        ).fetchone()[0]

        if table_exists:
            df = align_snapshot_schema(con, source.table_name, df)
            con.execute(
                f"DELETE FROM {quote_identifier(source.table_name)} "
                "WHERE CAST(data_snapshot AS DATE) = CAST(? AS DATE)",
                [snapshot_at],
            )
            con.register("snapshot_df", df)
            columns_sql = ", ".join(quote_identifier(column) for column in df.columns)
            con.execute(
                f"INSERT INTO {quote_identifier(source.table_name)} ({columns_sql}) "
                f"SELECT {columns_sql} FROM snapshot_df"
            )
            keep_latest_snapshot_per_day(con, source.table_name)
        else:
            con.register("snapshot_df", df)
            con.execute(f"CREATE TABLE {quote_identifier(source.table_name)} AS SELECT * FROM snapshot_df")

        return len(df), "sucesso", f"Snapshot inserido a partir de {source.csv_path}"
    except Exception as exc:
        return 0, "erro", f"Falha ao inserir em {source.table_name}: {exc}"
    finally:
        try:
            con.unregister("snapshot_df")
        except Exception:
            pass


def main() -> None:
    """Executa a rotina de snapshot para todas as bases configuradas."""

    snapshot_at = datetime.now()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    log("=" * 80)
    log("INICIO DO SNAPSHOT HISTORICO DUCKDB")
    log("=" * 80)
    log(f"Banco: {DB_PATH}")
    log(f"Data snapshot: {snapshot_at:%Y-%m-%d %H:%M:%S}")

    with duckdb.connect(str(DB_PATH)) as con:
        ensure_control_table(con)

        for source in SNAPSHOT_SOURCES:
            log("-" * 80)
            log(f"Processando {source.csv_path} -> {source.table_name}")
            rows, status, message = append_snapshot(con, source, snapshot_at)
            append_control_row(con, snapshot_at, source.table_name, rows, status, message)

            symbol = {
                "sucesso": "SUCESSO",
                "aviso": "AVISO",
                "erro": "ERRO",
            }[status]
            log(f"{symbol}: {message}")
            log(f"Linhas inseridas: {rows}")

    log("=" * 80)
    log("FIM DO SNAPSHOT HISTORICO DUCKDB")
    log("=" * 80)


if __name__ == "__main__":
    main()
