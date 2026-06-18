# MoboExpress — PRD

## Problem Statement
MoboExpress (tienda de móviles/servicio). Feature solicitado en este chat: implementar la UI del
**Cierre de caja diario (arqueo)** en `AccountingPanel.jsx` mostrando saldo inicial, entradas/salidas
y saldo final esperado, con botones de descarga directa CSV y PDF. Desplegar al compilar.

## Contexto
El chat anterior (otro fork) no viajó a esta rama; el entorno arrancó desde boilerplate.
Se implementó el feature completo (backend + frontend) en la rama `main`.

## Arquitectura
- Backend: FastAPI (`/app/backend/server.py`), MongoDB (motor), export PDF con fpdf2.
- Frontend: React 19 + Tailwind + framer-motion + lucide-react.

## Endpoints (prefijo /api)
- GET  /accounting/cash-closing?date=        -> resumen del arqueo
- POST /accounting/opening                   -> set saldo inicial
- POST /accounting/movements                 -> agregar movimiento
- GET  /accounting/movements?date=           -> listar
- DELETE /accounting/movements/{id}          -> eliminar
- GET  /accounting/cash-closing/export?date=&format=csv|pdf -> descarga
- POST /accounting/seed?date=                -> datos demo

## Implementado (2026-06-18)
- Resumen del arqueo en pantalla: saldo inicial, entradas, salidas, saldo final esperado.
- Tabla de movimientos del día con eliminar.
- Formularios: set saldo inicial y registrar movimiento (entrada/salida, método).
- Descarga directa CSV y PDF (verificado http 200, tipos correctos).
- Deployment readiness: PASS.

## Backlog / Próximos pasos
- P1: Conteo físico de billetes/monedas vs saldo esperado (diferencia/descuadre).
- P1: Autenticación por usuario (cajero) y auditoría.
- P2: Historial de cierres por rango de fechas y gráficas.
- P2: Cierre "bloqueado" (no editable tras confirmar).
