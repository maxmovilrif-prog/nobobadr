"""Limpieza de datos de prueba en nubo_produccion.
Conserva SOLO: el Fundador real (KEEP_ADMIN_EMAIL) + la colección cities.
Borra: el resto de usuarios, rides, orders, regions y colecciones derivadas.
Ejecutar manualmente cuando se confirme: python cleanup_production.py
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

URI = os.environ.get("MONGO_URL_OVERRIDE")
DB_NAME = os.environ.get("DB_NAME_OVERRIDE", "nubo_produccion")
KEEP_ADMIN_EMAIL = "badarbox1756@gmail.com"

WIPE_COLLECTIONS = [
    "rides", "orders", "regions", "transactions", "driver_payouts",
    "assignment_history", "audit_logs", "login_attempts", "password_reset_tokens",
]


async def main():
    client = AsyncIOMotorClient(URI, serverSelectionTimeoutMS=8000)
    db = client[DB_NAME]

    # 1) Borrar todos los usuarios excepto el Fundador real
    res_users = await db.users.delete_many({"email": {"$ne": KEEP_ADMIN_EMAIL}})
    print(f"Usuarios eliminados (conservado {KEEP_ADMIN_EMAIL}): {res_users.deleted_count}")

    # 2) Vaciar colecciones de actividad/datos de prueba (NO se toca 'cities')
    for col in WIPE_COLLECTIONS:
        res = await db[col].delete_many({})
        print(f"{col}: {res.deleted_count} eliminados")

    # 3) Verificación final
    print("\n=== ESTADO FINAL ===")
    print("users:", await db.users.count_documents({}), "(debe ser 1: el Fundador)")
    print("cities:", await db.cities.count_documents({}), "(debe seguir en 16)")
    for col in WIPE_COLLECTIONS:
        print(f"{col}:", await db[col].count_documents({}))
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
