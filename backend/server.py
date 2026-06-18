from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import io
import csv
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Literal, Optional
import uuid
from datetime import datetime, timezone, date as date_cls
from fpdf import FPDF


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="MoboExpress - Cierre de Caja")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# ----------------------------- Models -----------------------------
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StatusCheckCreate(BaseModel):
    client_name: str


class MovementCreate(BaseModel):
    date: str = Field(..., description="Fecha del movimiento en formato YYYY-MM-DD")
    type: Literal["entrada", "salida"]
    concept: str
    amount: float = Field(..., gt=0)
    method: str = Field(default="efectivo")


class Movement(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: str
    type: Literal["entrada", "salida"]
    concept: str
    amount: float
    method: str = "efectivo"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OpeningCreate(BaseModel):
    date: str
    saldo_inicial: float = Field(..., ge=0)


class CashCountSave(BaseModel):
    date: str
    counts: dict = Field(default_factory=dict, description="Mapa denominacion->cantidad, ej {'500': 2}")


class Reconciliation(BaseModel):
    efectivo_esperado: float
    total_contado: float
    diferencia: float
    estado: Literal["cuadra", "faltante", "sobrante"]
    counts: dict
    desglose: List[dict]


class CashClosingSummary(BaseModel):
    date: str
    saldo_inicial: float
    total_entradas: float
    total_salidas: float
    saldo_final_esperado: float
    efectivo_esperado: float
    movimientos: List[Movement]
    reconciliation: Optional[Reconciliation] = None


# Denominaciones MXN (billetes y monedas)
DENOMINATIONS = [1000, 500, 200, 100, 50, 20, 10, 5, 2, 1, 0.5]


# ----------------------------- Helpers -----------------------------
def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _build_reconciliation(efectivo_esperado: float, counts: dict) -> Reconciliation:
    desglose = []
    total = 0.0
    for denom in DENOMINATIONS:
        key = str(denom)
        qty = int(counts.get(key, 0) or 0)
        subtotal = round(denom * qty, 2)
        total += subtotal
        desglose.append({"denominacion": denom, "cantidad": qty, "subtotal": round(subtotal, 2)})
    total = round(total, 2)
    diferencia = round(total - efectivo_esperado, 2)
    if abs(diferencia) < 0.005:
        estado = "cuadra"
    elif diferencia < 0:
        estado = "faltante"
    else:
        estado = "sobrante"
    return Reconciliation(
        efectivo_esperado=round(efectivo_esperado, 2),
        total_contado=total,
        diferencia=diferencia,
        estado=estado,
        counts={str(d): int(counts.get(str(d), 0) or 0) for d in DENOMINATIONS},
        desglose=desglose,
    )


async def _build_summary(target_date: str) -> CashClosingSummary:
    opening = await db.cash_openings.find_one({"date": target_date}, {"_id": 0})
    saldo_inicial = float(opening["saldo_inicial"]) if opening else 0.0

    raw = await db.cash_movements.find({"date": target_date}, {"_id": 0}).to_list(1000)
    movimientos = [Movement(**m) for m in raw]
    movimientos.sort(key=lambda m: m.created_at)

    total_entradas = sum(m.amount for m in movimientos if m.type == "entrada")
    total_salidas = sum(m.amount for m in movimientos if m.type == "salida")
    saldo_final = saldo_inicial + total_entradas - total_salidas

    # Efectivo esperado en caja: solo movimientos en efectivo + fondo inicial
    efectivo_entradas = sum(m.amount for m in movimientos if m.type == "entrada" and m.method == "efectivo")
    efectivo_salidas = sum(m.amount for m in movimientos if m.type == "salida" and m.method == "efectivo")
    efectivo_esperado = saldo_inicial + efectivo_entradas - efectivo_salidas

    reconciliation = None
    count_doc = await db.cash_counts.find_one({"date": target_date}, {"_id": 0})
    if count_doc and count_doc.get("counts"):
        reconciliation = _build_reconciliation(efectivo_esperado, count_doc["counts"])

    return CashClosingSummary(
        date=target_date,
        saldo_inicial=round(saldo_inicial, 2),
        total_entradas=round(total_entradas, 2),
        total_salidas=round(total_salidas, 2),
        saldo_final_esperado=round(saldo_final, 2),
        efectivo_esperado=round(efectivo_esperado, 2),
        movimientos=movimientos,
        reconciliation=reconciliation,
    )


# ----------------------------- Routes -----------------------------
@api_router.get("/")
async def root():
    return {"message": "MoboExpress API - Cierre de caja diario"}


@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_obj = StatusCheck(**input.model_dump())
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    await db.status_checks.insert_one(doc)
    return status_obj


@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    return status_checks


@api_router.post("/accounting/opening", response_model=CashClosingSummary)
async def set_opening(payload: OpeningCreate):
    await db.cash_openings.update_one(
        {"date": payload.date},
        {"$set": {"date": payload.date, "saldo_inicial": float(payload.saldo_inicial)}},
        upsert=True,
    )
    return await _build_summary(payload.date)


@api_router.post("/accounting/movements", response_model=Movement)
async def add_movement(payload: MovementCreate):
    movement = Movement(**payload.model_dump())
    await db.cash_movements.insert_one(movement.model_dump())
    return movement


@api_router.get("/accounting/movements", response_model=List[Movement])
async def list_movements(date: Optional[str] = Query(default=None)):
    target = date or _today()
    raw = await db.cash_movements.find({"date": target}, {"_id": 0}).to_list(1000)
    return [Movement(**m) for m in raw]


@api_router.delete("/accounting/movements/{movement_id}")
async def delete_movement(movement_id: str):
    res = await db.cash_movements.delete_one({"id": movement_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    return {"deleted": True, "id": movement_id}


@api_router.get("/accounting/denominations")
async def get_denominations():
    return {"denominations": DENOMINATIONS}


@api_router.post("/accounting/cash-count", response_model=CashClosingSummary)
async def save_cash_count(payload: CashCountSave):
    clean = {str(d): int(payload.counts.get(str(d), 0) or 0) for d in DENOMINATIONS}
    await db.cash_counts.update_one(
        {"date": payload.date},
        {"$set": {"date": payload.date, "counts": clean,
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return await _build_summary(payload.date)


@api_router.get("/accounting/cash-closing", response_model=CashClosingSummary)
async def cash_closing(date: Optional[str] = Query(default=None)):
    target = date or _today()
    return await _build_summary(target)


@api_router.get("/accounting/cash-closing/export")
async def export_cash_closing(
    date: Optional[str] = Query(default=None),
    format: Literal["csv", "pdf"] = Query(default="csv"),
):
    target = date or _today()
    summary = await _build_summary(target)

    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["MoboExpress - Cierre de caja diario"])
        writer.writerow(["Fecha", target])
        writer.writerow([])
        writer.writerow(["Resumen"])
        writer.writerow(["Saldo inicial", f"{summary.saldo_inicial:.2f}"])
        writer.writerow(["Total entradas", f"{summary.total_entradas:.2f}"])
        writer.writerow(["Total salidas", f"{summary.total_salidas:.2f}"])
        writer.writerow(["Saldo final esperado", f"{summary.saldo_final_esperado:.2f}"])
        writer.writerow(["Efectivo esperado en caja", f"{summary.efectivo_esperado:.2f}"])
        if summary.reconciliation:
            r = summary.reconciliation
            writer.writerow([])
            writer.writerow(["Conteo de efectivo fisico"])
            writer.writerow(["Denominacion", "Cantidad", "Subtotal"])
            for d in r.desglose:
                if d["cantidad"]:
                    writer.writerow([f"{d['denominacion']:.2f}", d["cantidad"], f"{d['subtotal']:.2f}"])
            writer.writerow(["Total contado", "", f"{r.total_contado:.2f}"])
            writer.writerow(["Diferencia", "", f"{r.diferencia:.2f}"])
            writer.writerow(["Estado", "", r.estado.upper()])
        writer.writerow([])
        writer.writerow(["Hora", "Tipo", "Concepto", "Método", "Monto"])
        for m in summary.movimientos:
            hora = m.created_at[11:19] if len(m.created_at) >= 19 else ""
            signed = m.amount if m.type == "entrada" else -m.amount
            writer.writerow([hora, m.type, m.concept, m.method, f"{signed:.2f}"])

        data = buf.getvalue().encode("utf-8-sig")
        return StreamingResponse(
            io.BytesIO(data),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="cierre-caja-{target}.csv"'},
        )

    # PDF
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "MoboExpress", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "Cierre de caja diario", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, f"Fecha: {target}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    def kv_row(label, value, bold=False, color=(0, 0, 0)):
        pdf.set_font("Helvetica", "B" if bold else "", 11)
        pdf.set_text_color(*color)
        pdf.cell(120, 8, label, border=0)
        pdf.cell(0, 8, f"{value:,.2f}", border=0, align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

    pdf.set_fill_color(245, 245, 245)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 9, "Resumen del arqueo", border=0, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    kv_row("Saldo inicial", summary.saldo_inicial)
    kv_row("Total entradas", summary.total_entradas, color=(22, 130, 70))
    kv_row("Total salidas", summary.total_salidas, color=(190, 40, 40))
    kv_row("Saldo final esperado", summary.saldo_final_esperado, bold=True)
    kv_row("Efectivo esperado en caja", summary.efectivo_esperado)
    pdf.ln(5)

    if summary.reconciliation:
        r = summary.reconciliation
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 9, "Conteo de efectivo fisico", border=0, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(60, 7, "Denominacion", border="B")
        pdf.cell(40, 7, "Cantidad", border="B", align="R")
        pdf.cell(0, 7, "Subtotal", border="B", align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for d in r.desglose:
            if not d["cantidad"]:
                continue
            pdf.cell(60, 7, f"{d['denominacion']:,.2f}", border="B")
            pdf.cell(40, 7, str(d["cantidad"]), border="B", align="R")
            pdf.cell(0, 7, f"{d['subtotal']:,.2f}", border="B", align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        kv_row("Total contado", r.total_contado, bold=True)
        estado_color = {"cuadra": (22, 130, 70), "faltante": (190, 40, 40), "sobrante": (200, 130, 0)}[r.estado]
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*estado_color)
        pdf.cell(120, 8, f"Diferencia ({r.estado.upper()})")
        pdf.cell(0, 8, f"{r.diferencia:,.2f}", align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 9, "Detalle de movimientos", border=0, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(20, 7, "Hora", border="B")
    pdf.cell(25, 7, "Tipo", border="B")
    pdf.cell(85, 7, "Concepto", border="B")
    pdf.cell(30, 7, "Método", border="B")
    pdf.cell(0, 7, "Monto", border="B", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    if not summary.movimientos:
        pdf.cell(0, 7, "Sin movimientos registrados", new_x="LMARGIN", new_y="NEXT")
    for m in summary.movimientos:
        hora = m.created_at[11:19] if len(m.created_at) >= 19 else ""
        signed = m.amount if m.type == "entrada" else -m.amount
        concept = m.concept if len(m.concept) <= 45 else m.concept[:42] + "..."
        pdf.cell(20, 7, hora, border="B")
        pdf.cell(25, 7, m.type.capitalize(), border="B")
        pdf.cell(85, 7, concept, border="B")
        pdf.cell(30, 7, m.method, border="B")
        if m.type == "entrada":
            pdf.set_text_color(22, 130, 70)
        else:
            pdf.set_text_color(190, 40, 40)
        pdf.cell(0, 7, f"{signed:,.2f}", border="B", align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

    out = pdf.output()
    pdf_bytes = bytes(out)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cierre-caja-{target}.pdf"'},
    )


@api_router.post("/accounting/seed")
async def seed_demo(date: Optional[str] = Query(default=None)):
    target = date or _today()
    await db.cash_openings.delete_many({"date": target})
    await db.cash_movements.delete_many({"date": target})
    await db.cash_counts.delete_many({"date": target})

    await db.cash_openings.insert_one({"date": target, "saldo_inicial": 500.0})
    demo = [
        ("entrada", "Venta iPhone 13 - mostrador", 850.0, "tarjeta"),
        ("entrada", "Venta accesorios (fundas/cargadores)", 120.5, "efectivo"),
        ("salida", "Pago proveedor micas templadas", 200.0, "efectivo"),
        ("entrada", "Reparación pantalla Samsung A52", 65.0, "efectivo"),
        ("salida", "Caja chica - limpieza", 35.0, "efectivo"),
        ("entrada", "Venta audífonos bluetooth", 49.99, "transferencia"),
    ]
    for t, c, a, method in demo:
        mv = Movement(date=target, type=t, concept=c, amount=a, method=method)
        await db.cash_movements.insert_one(mv.model_dump())

    return await _build_summary(target)


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
