"""Rutas de comunicaciones por email (Resend) — solo Fundador."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from core import get_current_admin
import email_service

router = APIRouter()


class TestEmailRequest(BaseModel):
    to: EmailStr
    subject: str = Field(default="Prueba de Nubo Express", min_length=2)
    message: str = Field(default="Este es un correo de prueba enviado desde el panel del Fundador.", min_length=2)


@router.get("/admin/email/status")
async def email_status(current_user: dict = Depends(get_current_admin)):
    """Indica si el email transaccional (Resend) está configurado."""
    return {
        "configured": email_service.is_configured(),
        "sender": email_service.SENDER_EMAIL,
        "provider": "resend",
    }


@router.post("/admin/email/test")
async def send_test_email(payload: TestEmailRequest, current_user: dict = Depends(get_current_admin)):
    """Envía un correo de prueba (solo Fundador) para validar la configuración de Resend."""
    if not email_service.is_configured():
        raise HTTPException(status_code=503, detail="Email no configurado: falta RESEND_API_KEY")
    result = await email_service.send_email(
        payload.to, payload.subject, f"<p>{payload.message}</p>"
    )
    if not result.get("sent"):
        raise HTTPException(status_code=502, detail=f"No se pudo enviar: {result.get('reason')}")
    return {"message": "Correo de prueba enviado", "email_id": result.get("id")}
