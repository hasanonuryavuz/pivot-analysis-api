"""Lazy filtreleme/toplama ve küçük sonuç üzerinde dinamik pivot."""
from datetime import date
from time import perf_counter
from typing import Literal
import polars as pl

Axis = Literal["Tarih", "Bolge", "Kategori"]

def build_pivot(data: pl.DataFrame, row: Axis, column: Axis,
                start_date: date | None = None, end_date: date | None = None) -> dict:
    if row not in ("Tarih", "Bolge", "Kategori") or column not in ("Tarih", "Bolge", "Kategori"):
        raise ValueError("Geçersiz eksen.")
    if row == column:
        raise ValueError("Satır ve sütun eksenleri farklı olmalıdır.")
    if start_date and end_date and start_date > end_date:
        raise ValueError("Başlangıç tarihi bitiş tarihinden sonra olamaz.")
    started = perf_counter()
    query = data.lazy()
    if start_date:
        query = query.filter(pl.col("Tarih") >= start_date)
    if end_date:
        query = query.filter(pl.col("Tarih") <= end_date)
    # Milyon satır burada lazy planla taranır. Satır sayısı da aynı gruplardan hesaplanır.
    grouped = query.group_by([row, column]).agg(
        pl.col("Satis_Adedi").sum(), pl.len().alias("matched_rows")
    ).collect()
    matched = int(grouped["matched_rows"].sum() or 0)
    total = int(grouped["Satis_Adedi"].sum() or 0)
    if grouped.is_empty():
        columns, records = [row], []
    else:
        # Tarihi ISO metne çevirerek JSON anahtarlarını ve değerlerini tutarlı tutarız.
        grouped = grouped.with_columns(pl.col(row).cast(pl.String), pl.col(column).cast(pl.String))
        table = grouped.pivot(on=column, index=row, values="Satis_Adedi", aggregate_function="sum", sort_columns=True).fill_null(0).sort(row)
        columns, records = table.columns, table.to_dicts()
    return {
        "meta": {"row": row, "column": column, "aggregation": "sum", "source_rows": data.height,
                 "matched_rows": matched, "total_sales": total, "result_rows": len(records),
                 "result_columns": len(columns) - 1, "elapsed_ms": round((perf_counter()-started)*1000, 3)},
        "columns": columns, "data": records,
    }
