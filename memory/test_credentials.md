# Test Credentials — Nubo

## QA accounts (created by agent, known passwords)
- Customer: `qa_customer@nubo.com` / `Test1234!`
- Admin: `admin@nubo.com` / `Admin1234!`  (role: admin, fleet dashboard at /admin)

## Notes
- Other seeded accounts exist (cliente1@test.com, restaurante@test.com, repartidor@test.com, etc.) but their passwords are unknown.
- Register endpoint: POST /api/auth/register
- AI Smart Search endpoint: POST /api/search/smart  body: {"query": "tengo hambre"}
