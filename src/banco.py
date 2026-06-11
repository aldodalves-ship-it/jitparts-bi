"""Camada de persistencia local com DuckDB."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


class DuckDBStore:
    """Repositorio simples para historico analitico."""

    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.db_path))

    def init_database(self) -> None:
        """Cria tabelas basicas para expansao incremental."""

        with self.connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS fact_sales (
                    order_id VARCHAR,
                    date_created TIMESTAMP,
                    mlb VARCHAR,
                    sku VARCHAR,
                    brand VARCHAR,
                    category VARCHAR,
                    logistic_type VARCHAR,
                    fulfillment_type VARCHAR,
                    quantity INTEGER,
                    gross_revenue DOUBLE,
                    net_revenue DOUBLE,
                    cmv DOUBLE,
                    fees DOUBLE,
                    ads_cost DOUBLE,
                    shipping_cost DOUBLE,
                    gross_profit DOUBLE,
                    ebitda DOUBLE,
                    net_profit DOUBLE,
                    status VARCHAR,
                    cancellation_flag BOOLEAN,
                    return_flag BOOLEAN,
                    stock INTEGER,
                    source VARCHAR,
                    loaded_at TIMESTAMP DEFAULT current_timestamp
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS dim_items (
                    mlb VARCHAR PRIMARY KEY,
                    sku VARCHAR,
                    title VARCHAR,
                    brand VARCHAR,
                    category VARCHAR,
                    price DOUBLE,
                    available_quantity INTEGER,
                    logistic_type VARCHAR,
                    updated_at TIMESTAMP DEFAULT current_timestamp
                )
                """
            )

    def save_dataframe(self, table_name: str, df: pd.DataFrame, mode: str = "append") -> None:
        """Salva um DataFrame em uma tabela DuckDB."""

        if df.empty:
            return
        with self.connect() as con:
            con.register("df_to_save", df)
            if mode == "replace":
                con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df_to_save")
            else:
                target_columns = [
                    row[1]
                    for row in con.execute(f"PRAGMA table_info('{table_name}')").fetchall()
                    if row[1] in df.columns
                ]
                if not target_columns:
                    return
                columns_sql = ", ".join(target_columns)
                con.execute(
                    f"INSERT INTO {table_name} ({columns_sql}) "
                    f"SELECT {columns_sql} FROM df_to_save"
                )

    def read_dataframe(self, query: str) -> pd.DataFrame:
        with self.connect() as con:
            return con.execute(query).df()
