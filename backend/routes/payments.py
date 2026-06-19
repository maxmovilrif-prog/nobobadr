"""Rutas de pagos (Stripe)."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Request
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

from core import db, get_current_user, get_current_admin, STRIPE_API_KEY, STRIPE_MODE
from models import PaymentTransaction
from assignments import auto_assign_order

router = APIRouter()


@router.get("/admin/payments/status")
async def payments_status(current_user: dict = Depends(get_current_admin)):
    """Estado de Stripe (solo Fundador): modo test/live, sin exponer la clave."""
    key = STRIPE_API_KEY or ''
    return {
        "mode": STRIPE_MODE,
        "live": STRIPE_MODE == "live",
        "key_prefix": (key[:8] + "…") if key else None,
    }


@router.post("/payments/create-checkout")
async def create_checkout_session(order_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({'id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order['customer_id'] != current_user['id']:
        raise HTTPException(status_code=403, detail="Not authorized")

    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)

    origin = request.headers.get('origin', host_url.rstrip('/'))
    success_url = f"{origin}/order-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/orders"

    checkout_request = CheckoutSessionRequest(
        amount=float(order['total_amount']),
        currency="eur",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={'order_id': order_id, 'user_id': current_user['id']}
    )

    session = await stripe_checkout.create_checkout_session(checkout_request)

    transaction = PaymentTransaction(
        session_id=session.session_id,
        order_id=order_id,
        user_id=current_user['id'],
        amount=float(order['total_amount']),
        currency="eur",
        payment_status="pending",
        metadata={'order_id': order_id}
    )
    doc = transaction.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.payment_transactions.insert_one(doc)

    await db.orders.update_one(
        {'id': order_id},
        {'$set': {'payment_session_id': session.session_id}}
    )
    return {'url': session.url, 'session_id': session.session_id}


@router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    transaction = await db.payment_transactions.find_one({'session_id': session_id}, {'_id': 0})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if transaction['payment_status'] == 'paid':
        return transaction

    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)

    status = await stripe_checkout.get_checkout_status(session_id)

    await db.payment_transactions.update_one(
        {'session_id': session_id},
        {'$set': {'payment_status': status.payment_status, 'updated_at': datetime.now(timezone.utc).isoformat()}}
    )
    if status.payment_status == 'paid':
        await db.orders.update_one(
            {'id': transaction['order_id']},
            {'$set': {'payment_status': 'paid'}}
        )
        try:
            await auto_assign_order(transaction['order_id'])
        except Exception:
            pass
    return {
        'session_id': session_id,
        'payment_status': status.payment_status,
        'status': status.status,
        'amount': status.amount_total / 100,
        'currency': status.currency
    }


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    try:
        host_url = str(request.base_url)
        webhook_url = f"{host_url}api/webhook/stripe"
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        if webhook_response.payment_status == 'paid':
            transaction = await db.payment_transactions.find_one({'session_id': webhook_response.session_id}, {'_id': 0})
            if transaction and transaction['payment_status'] != 'paid':
                await db.payment_transactions.update_one(
                    {'session_id': webhook_response.session_id},
                    {'$set': {'payment_status': 'paid', 'updated_at': datetime.now(timezone.utc).isoformat()}}
                )
                await db.orders.update_one(
                    {'id': transaction['order_id']},
                    {'$set': {'payment_status': 'paid'}}
                )
                try:
                    await auto_assign_order(transaction['order_id'])
                except Exception:
                    pass
        return {'status': 'success'}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
