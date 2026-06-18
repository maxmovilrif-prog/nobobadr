# Auth Testing — MoboExpress

## DB checks
mongosh; use test_database
db.users.find({role:"admin"}).pretty()
- bcrypt hash starts with `$2b$`
- index on users.email (unique)

## API checks (use external REACT_APP_BACKEND_URL)
1) Login admin:
curl -s -X POST $API/api/auth/login -H "Content-Type: application/json" -d '{"email":"admin@moboexpress.com","password":"admin123"}'
-> returns access_token + user

2) Me:
curl -s $API/api/auth/me -H "Authorization: Bearer <token>"

3) Orders + COD->cash flow:
- POST /api/orders (city Tanger -> currency MAD; city Algeciras/Spain -> EUR)
- POST /api/assignments {order_id, rider_id}
- PATCH /api/orders/{id}/status {"status":"delivered"} with payment_method cod_cash
  -> order.paid=true, cash_movement_id set
  -> GET /api/accounting/cash-closing shows an "entrada" linked by order_id

4) WebSocket: connect ws(s)://<host>/api/ws?token=<access_token>
   -> receives {"type":"connected"}; broadcasts order_created/order_status/rider_location.
