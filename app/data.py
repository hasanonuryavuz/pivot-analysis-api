"""Tekrarlanabilir satış verisini bir kez üretir; veritabanı kullanmaz."""
from datetime import date
import numpy as np
import polars as pl

REGIONS = ["Akdeniz", "Dogu Anadolu", "Ege", "Guneydogu Anadolu", "Ic Anadolu", "Karadeniz", "Marmara"]
CATEGORIES = ["Elektronik", "Gida", "Giyim", "Kitap", "Mobilya"]

def generate_sales(rows: int = 1_000_000, seed: int = 42) -> pl.DataFrame:
    if rows < 1:
        raise ValueError("Satır sayısı pozitif olmalıdır.")
    rng = np.random.default_rng(seed)
    # NumPy yalnızca vektörleştirilmiş rastgele sayı üretimi için kullanılır.
    # Tablo, tarih dönüşümü ve tüm analiz işlemleri Polars ile yapılır.
    return pl.DataFrame({
        "Tarih": rng.integers(0, 365, size=rows, dtype=np.int32),
        "Bolge": rng.choice(REGIONS, size=rows),
        "Kategori": rng.choice(CATEGORIES, size=rows),
        "Satis_Adedi": rng.integers(1, 101, size=rows, dtype=np.int64),
    }).with_columns(
        (pl.lit(date(2025, 1, 1)) + pl.duration(days=pl.col("Tarih"))).cast(pl.Date).alias("Tarih"),
        pl.col("Bolge").cast(pl.Categorical),
        pl.col("Kategori").cast(pl.Categorical),
    )
