"""Búsqueda inteligente en lenguaje natural (IA)."""
import json
import re
import uuid
from typing import List

from fastapi import APIRouter, HTTPException
from emergentintegrations.llm.chat import LlmChat, UserMessage

from core import db, logger, EMERGENT_LLM_KEY
from models import SmartSearchRequest

router = APIRouter()

VALID_CATEGORIES = ["restaurant", "supermarket", "courier", "vehicles", "electronics", "transport"]


def _extract_json(text: str) -> dict:
    """Extrae el primer bloque JSON de la respuesta del LLM de forma robusta."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
    return {}


@router.post("/search/smart")
async def smart_search(req: SmartSearchRequest):
    """
    Búsqueda en lenguaje natural. Interpreta la intención del usuario (ej. "tengo hambre")
    usando el LLM y devuelve negocios y productos relevantes ordenados.
    """
    query = (req.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="La búsqueda no puede estar vacía")

    categories: List[str] = []
    keywords: List[str] = []
    ai_message = ""

    if EMERGENT_LLM_KEY:
        try:
            system_message = (
                "Eres el asistente de búsqueda de Nubo, un marketplace multiservicio en España. "
                "Las categorías disponibles son: restaurant (comida/restaurantes), supermarket (supermercado/alimentación), "
                "courier (paquetería/envíos), vehicles (vehículos/coches), electronics (electrónica/tecnología), "
                "transport (NuboRide/viajes en coche con conductor). "
                "Analiza la consulta del usuario e identifica su intención. "
                "Responde ÚNICAMENTE con un objeto JSON válido (sin texto adicional, sin markdown) con esta estructura exacta: "
                '{\"categories\": [lista de categorías relevantes de la lista permitida], '
                '\"keywords\": [lista de palabras clave en español para buscar productos], '
                '\"message\": \"un mensaje corto y amable en el idioma del usuario explicando qué le mostramos\"}. '
                "Ejemplo: para 'tengo hambre' devuelve categories ['restaurant','supermarket'] y un mensaje amable."
            )
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"search-{uuid.uuid4()}",
                system_message=system_message,
            ).with_model("openai", "gpt-5.4-mini")
            response = await chat.send_message(UserMessage(text=query))
            parsed = _extract_json(response if isinstance(response, str) else str(response))
            categories = [c for c in parsed.get("categories", []) if c in VALID_CATEGORIES]
            keywords = [str(k).lower() for k in parsed.get("keywords", []) if k]
            ai_message = parsed.get("message", "")
        except Exception as e:
            logger.error(f"Smart search LLM error: {e}")

    if not keywords:
        keywords = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 2]
    if not ai_message:
        ai_message = "Esto es lo que encontramos para tu búsqueda:"

    business_query: dict = {}
    or_conditions = []
    if categories:
        or_conditions.append({"category": {"$in": categories}})
    if keywords:
        kw_regex = "|".join(re.escape(k) for k in keywords)
        or_conditions.append({"name": {"$regex": kw_regex, "$options": "i"}})
        or_conditions.append({"description": {"$regex": kw_regex, "$options": "i"}})
    if or_conditions:
        business_query = {"$or": or_conditions}

    businesses = await db.businesses.find(business_query, {'_id': 0}).to_list(50)

    products = []
    if keywords:
        kw_regex = "|".join(re.escape(k) for k in keywords)
        products = await db.products.find({
            "$or": [
                {"name": {"$regex": kw_regex, "$options": "i"}},
                {"description": {"$regex": kw_regex, "$options": "i"}},
                {"category": {"$regex": kw_regex, "$options": "i"}},
            ]
        }, {'_id': 0}).to_list(50)

    return {
        "message": ai_message,
        "categories": categories,
        "keywords": keywords,
        "businesses": businesses,
        "products": products,
    }
