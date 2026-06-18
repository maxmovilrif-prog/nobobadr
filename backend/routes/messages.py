"""Rutas de mensajería (chat por pedido)."""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends

from core import db, get_current_user
from models import Message, MessageCreate

router = APIRouter()


@router.post("/messages", response_model=Message)
async def send_message(message_data: MessageCreate, current_user: dict = Depends(get_current_user)):
    message_dict = message_data.model_dump()
    message_dict['sender_id'] = current_user['id']
    message_dict['sender_role'] = current_user['role']

    message = Message(**message_dict)
    doc = message.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()

    await db.messages.insert_one(doc)
    return message


@router.get("/messages/{order_id}", response_model=List[Message])
async def get_messages(order_id: str, current_user: dict = Depends(get_current_user)):
    messages = await db.messages.find({'order_id': order_id}, {'_id': 0}).sort('created_at', 1).to_list(1000)
    for message in messages:
        if isinstance(message.get('created_at'), str):
            message['created_at'] = datetime.fromisoformat(message['created_at'])
    return messages
