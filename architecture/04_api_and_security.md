# Sections 4-5: API Design & Security (Standalone)

## Section 4: API Conventions

### Base URL
```
http://localhost:8000/api/v1/
```
No HTTPS required — traffic never leaves the machine.

### Response Envelope (unchanged)
```json
{
  "success": true,
  "data": { ... },
  "message": "Asset created successfully"
}
```

### Pagination (unchanged)
```json
{
  "success": true,
  "data": [ ... ],
  "pagination": { "page": 1, "per_page": 20, "total_items": 142, "total_pages": 8 }
}
```

### Error Response (unchanged)
```json
{
  "success": false,
  "error": { "code": "VALIDATION_ERROR", "message": "...", "details": [...] }
}
```

### Currency Convention
- **API** accepts/returns rupees as `float` (e.g., `1234.56`)
- **Database** stores paise as `integer` (e.g., `123456`)
- Conversion happens in service layer transparently

---

## 4.2 — Complete Endpoint Specification (Standalone)

### Auth (Simplified — no JWT, no email)

```
POST /api/v1/auth/login
Auth: public
Body: { "email": "str", "password": "str" }
200: { "data": { "user": {...}, "session_token": "str" } }
Note: Returns a simple session token. Stored in localStorage by frontend.

POST /api/v1/auth/logout
Auth: session token
200: { "message": "Logged out" }

PUT /api/v1/auth/change-password
Auth: session token
Body: { "current_password": "str", "new_password": "str" }
200: { "message": "Password changed" }

POST /api/v1/auth/reset-password-local
Auth: public
Body: { "email": "str", "security_answer": "str", "new_password": "str" }
200: { "message": "Password reset successful" }
Note: No email flow. Uses security question set during onboarding.

PUT /api/v1/auth/change-master-password
Auth: session token
Body: { "current_master_password": "str", "new_master_password": "str" }
200: { "message": "Master password changed, vault re-encrypted" }
```

### Registration (First-time setup only)
```
POST /api/v1/auth/register
Auth: public
Body: { "full_name", "email", "password", "security_question", "security_answer" }
200: { "data": { "user_id", "email" } }
Note: Only works if no user exists yet (single-user app).
```

### User & Setup (unchanged endpoints, same request/response)
```
GET    /api/v1/users/me
PUT    /api/v1/users/me
POST   /api/v1/users/me/avatar              (multipart file upload)
GET    /api/v1/users/me/preferences
PUT    /api/v1/users/me/preferences
POST   /api/v1/users/setup-wizard           Body: { step: 1|2|3, data: {...} }
```

### Assets (unchanged)
```
GET    /api/v1/assets?type=mutual-fund&page=1&per_page=20&search=HDFC
POST   /api/v1/assets
GET    /api/v1/assets/{id}
PUT    /api/v1/assets/{id}
DELETE /api/v1/assets/{id}
POST   /api/v1/assets/bulk-upload            (multipart CSV/Excel)
POST   /api/v1/assets/{id}/images            (multipart image)
DELETE /api/v1/assets/{id}/images/{image_id}
```

### SIP Schedules (unchanged)
```
GET    /api/v1/sip-schedules
POST   /api/v1/sip-schedules
PUT    /api/v1/sip-schedules/{id}
PUT    /api/v1/sip-schedules/{id}/pause
PUT    /api/v1/sip-schedules/{id}/resume
DELETE /api/v1/sip-schedules/{id}
```

### Expenses (unchanged)
```
GET    /api/v1/expenses?month=6&year=2025&category_id=uuid&spent_by_id=uuid
POST   /api/v1/expenses
PUT    /api/v1/expenses/{id}
DELETE /api/v1/expenses/{id}
GET    /api/v1/expenses/calendar?month=6&year=2025
GET    /api/v1/expenses/category-summary?month=6&year=2025
GET    /api/v1/expenses/categories
POST   /api/v1/expenses/categories
PUT    /api/v1/expenses/categories/{id}
DELETE /api/v1/expenses/categories/{id}
PUT    /api/v1/expenses/categories/reorder
GET    /api/v1/household-members
POST   /api/v1/household-members
PUT    /api/v1/household-members/{id}
DELETE /api/v1/household-members/{id}
```

### Vault (unchanged except no rate limiting)
```
POST   /api/v1/vault/unlock                 Body: { master_password }
POST   /api/v1/vault/lock
GET    /api/v1/vault/credentials
POST   /api/v1/vault/credentials
PUT    /api/v1/vault/credentials/{id}
DELETE /api/v1/vault/credentials/{id}
POST   /api/v1/vault/bulk-import             (multipart CSV)
POST   /api/v1/vault/export                  Body: { format, master_password }
POST   /api/v1/vault/generate-password       Body: { length, uppercase, numbers, symbols }
GET    /api/v1/vault/audit-log
```

### Reports (synchronous now — no async queue)
```
GET    /api/v1/reports/portfolio-summary
GET    /api/v1/reports/financial-health
GET    /api/v1/reports/benchmark?benchmark=nifty50&period=1Y
GET    /api/v1/reports/expense-summary?months=6
POST   /api/v1/reports/export                Body: { format, sections[], date_from, date_to }
  200: { "data": { "file_path": "/exports/report_2025-06-10.pptx" } }
  Note: Generated synchronously. Returns file path immediately (no polling).
GET    /api/v1/reports/download/{filename}   → Direct file download from local storage
```

### Notifications (unchanged)
```
GET    /api/v1/notifications?is_read=false&page=1
GET    /api/v1/notifications/count
PUT    /api/v1/notifications/{id}/read
PUT    /api/v1/notifications/read-all
DELETE /api/v1/notifications/{id}
```

### Settings (simplified — local operations)
```
POST   /api/v1/settings/backup               → Copies DB file to ~/.finvault/backups/
POST   /api/v1/settings/restore              Body: { backup_filename }
GET    /api/v1/settings/backups               → Lists available backup files
POST   /api/v1/settings/export-all-data       → Generates JSON export of all data
POST   /api/v1/settings/import-data           (multipart JSON)
DELETE /api/v1/settings/clear-expenses
DELETE /api/v1/settings/clear-assets
DELETE /api/v1/settings/reset-app             Body: { password }
GET    /api/v1/settings/app-info              → { version, db_size, storage_used }
```

---

## Section 5: Security Design (Standalone)

### 5.1 — Authentication (Simplified)

```
User opens browser → http://localhost:8000
  → FastAPI checks: any user exists in DB?
    → No  → Redirect to /setup (first-time onboarding)
    → Yes → Show login screen

Login flow:
  1. User enters email + password
  2. Server verifies Argon2id hash
  3. Server generates random session token (secrets.token_urlsafe(32))
  4. Token stored in user_sessions table + in-memory dict
  5. Token returned to frontend, stored in localStorage
  6. All subsequent requests include: Authorization: Bearer <session_token>
  7. Auto-lock: after N minutes of no API calls, session invalidated in memory
  8. User must re-enter password to continue
```

No JWT, no cookies, no refresh rotation, no CORS, no CSRF. Just a session token on localhost.

### 5.2 — Vault Encryption (UNCHANGED)
- **Key derivation**: PBKDF2-SHA256, 600K iterations, per-user salt
- **Encryption**: AES-256-CBC, random IV per credential
- **Encrypted fields**: service_name, url, username, password, notes
- **Master password forgotten**: Data permanently lost (same as cloud version)
- **Master password change**: Decrypt all → re-encrypt all in one transaction

### 5.3 — Password Hashing (UNCHANGED)
- Argon2id (memory=65536 KB, iterations=3, parallelism=4)

### 5.4 — Password Recovery (Local, No Email)
```
Instead of email reset flow:
1. During onboarding, user sets a security question + answer
2. Answer is Argon2id-hashed and stored
3. To reset password: verify security answer → set new password
4. CLI escape hatch: python -m finvault reset-password (for advanced users)
```

### 5.5 — What's NOT Needed for Standalone
| Security Measure | Status | Why |
|---|---|---|
| CORS | ❌ Removed | Same-origin localhost |
| CSRF | ❌ Removed | No cookies, token in header |
| Rate limiting | ❌ Removed | Local app, no abuse |
| Security headers (HSTS, CSP) | ❌ Removed | No TLS, localhost only |
| SSL/TLS | ❌ Removed | Traffic never leaves machine |
| Sentry error tracking | ❌ Removed | Local log file instead |

### 5.6 — What Stays
| Security Measure | Status |
|---|---|
| Argon2id password hashing | ✅ Unchanged |
| AES-256-CBC vault encryption | ✅ Unchanged |
| PBKDF2 key derivation (600K iterations) | ✅ Unchanged |
| Input validation (Pydantic) | ✅ Unchanged |
| SQL injection prevention (SQLAlchemy ORM) | ✅ Unchanged |
| Audit logging (vault access, data deletion) | ✅ Unchanged |
| Auto-lock after inactivity | ✅ Unchanged |
