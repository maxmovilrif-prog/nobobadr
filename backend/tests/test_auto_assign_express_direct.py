"""Direct DB test: verifies auto_assign_order uses origin_lat/origin_lng for express orders.

Simulates Stripe webhook by marking the order paid in DB, then calls auto_assign_order().
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")
# Load env (server reads from backend/.env via dotenv inside server.py)
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    # find Madrid driver
    drv = await db.users.find_one({"email": "bee.madrid@nuboexpress.com"}, {"_id": 0})
    assert drv, "Madrid driver not seeded"
    print("[OK] Driver:", drv["id"], "role=", drv.get("role"), "available=", drv.get("is_available"))

    # ensure availability & location near Madrid
    await db.users.update_one(
        {"id": drv["id"]},
        {"$set": {
            "is_available": True,
            "current_location": {"lat": 40.4168, "lng": -3.7038},
        }}
    )

    # find a customer
    cust = await db.users.find_one({"email": "cliente@nubotest.com"}, {"_id": 0})
    assert cust

    # Insert express order with origin in Madrid, payment_status=paid, no driver
    order_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    order_doc = {
        "id": order_id,
        "customer_id": cust["id"],
        "business_id": None,
        "items": [],
        "total_amount": 8.0,
        "delivery_address": "Madrid Atocha",
        "status": "pending",
        "payment_status": "paid",
        "driver_id": None,
        "order_type": "express",
        "vehicle_type": "motorcycle",
        "origin_name": "Madrid Sol",
        "origin_lat": 40.4168,
        "origin_lng": -3.7038,
        "destination_name": "Madrid Atocha",
        "destination_lat": 40.4070,
        "destination_lng": -3.6907,
        "distance_km": 3,
        "eta_mins": 10,
        "currency": "EUR",
        "city_id": None,  # express → NO city; auto-assign should still work via origin
        "created_at": now,
        "updated_at": now,
    }
    await db.orders.insert_one(order_doc)
    print("[OK] Inserted express order with payment_status=paid, city_id=None, origin near Madrid")

    # Import after DB ready (server module connects to DB on import — that's OK)
    from server import auto_assign_order

    res = await auto_assign_order(order_id)
    print("[INFO] auto_assign_order result:", res)

    final = await db.orders.find_one({"id": order_id}, {"_id": 0})
    print("[INFO] Final order driver_id:", final.get("driver_id"), "status:", final.get("status"))

    # Cleanup
    await db.orders.delete_one({"id": order_id})

    if final.get("driver_id"):
        print("[PASS] Express auto-assign uses origin coords (assigned without city_id).")
        return 0
    else:
        # could be that driver was not eligible (no current_location set early enough)
        print("[FAIL] Express order not auto-assigned despite available driver near origin.")
        return 1


if __name__ == "__main__":
    code = asyncio.run(main())
    sys.exit(code)
