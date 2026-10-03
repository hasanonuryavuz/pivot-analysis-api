"""FastAPI giriş noktası. Başlangıçta bir milyon satır RAM'e yüklenir."""
from contextlib import asynccontextmanager
from datetime import date
from time import perf_counter
from fastapi import FastAPI, HTTPException, Query, Request
from app.analysis import Axis, build_pivot
from app.data import generate_sales


def create_app(rows: int = 1_000_000, seed: int = 42) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        started = perf_counter()
        app.state.sales = generate_sales(rows, seed)
        app.state.generation_ms = round((perf_counter()-started)*1000, 3)
        yield
        del app.state.sales

    api = FastAPI(title="Devasa Veri · Pivot Analiz API", version="1.0.0",
                  description="RAM üzerinde Polars lazy analiz ve dinamik satış pivotu.", lifespan=lifespan)

    @api.get("/", tags=["Bilgi"])
    def home():
        return {"project": "Pivot Analiz API", "docs": "/docs", "example": "/pivot?row=Bolge&column=Kategori"}

    @api.get("/health", tags=["Bilgi"])
    def health(request: Request):
        return {"status": "ok", "rows": request.app.state.sales.height}

    @api.get("/dataset", tags=["Bilgi"])
    def dataset(request: Request):
        data = request.app.state.sales
        return {"rows": data.height, "estimated_table_mib": round(data.estimated_size("mb"), 3),
                "generation_ms": request.app.state.generation_ms,
                "schema": {key: str(value) for key, value in data.schema.items()},
                "axes": ["Tarih", "Bolge", "Kategori"], "sample": data.head(5).to_dicts()}

    # Senkron endpoint FastAPI tarafından thread pool'da çalıştırılır;
    # CPU işi async event loop üzerinde çalıştırılmaz.
    @api.get("/pivot", tags=["Analiz"])
    def pivot(request: Request, row: Axis = Query("Bolge", description="Satır ekseni"),
              column: Axis = Query("Kategori", description="Sütun ekseni"),
              start_date: date | None = Query(None, description="Dahil, YYYY-MM-DD"),
              end_date: date | None = Query(None, description="Dahil, YYYY-MM-DD")):
        try:
            return build_pivot(request.app.state.sales, row, column, start_date, end_date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return api

app = create_app()
