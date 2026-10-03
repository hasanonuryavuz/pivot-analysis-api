"""Çalıştır: python -m scripts.benchmark"""
import json
import platform
from statistics import median
from time import perf_counter
import polars as pl
from app.analysis import build_pivot
from app.data import generate_sales

if __name__ == "__main__":
    started = perf_counter()
    data = generate_sales()
    generation_ms = (perf_counter()-started)*1000
    results = [build_pivot(data, "Bolge", "Kategori") for _ in range(7)]
    assert all(item["meta"]["total_sales"] == int(data["Satis_Adedi"].sum()) for item in results)
    print(json.dumps({"python": platform.python_version(), "polars": pl.__version__, "rows": data.height,
                      "generation_ms": round(generation_ms, 3), "estimated_table_mib": round(data.estimated_size("mb"), 3),
                      "runs_ms": [item["meta"]["elapsed_ms"] for item in results],
                      "median_ms": median(item["meta"]["elapsed_ms"] for item in results),
                      "result_shape": [7, 5], "total_sales": results[0]["meta"]["total_sales"]}, indent=2))
