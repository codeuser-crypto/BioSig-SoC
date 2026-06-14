# FinVault — ER Diagram & Architecture (Standalone SQLite)

---

## 1. Entity-Relationship Diagram

```mermaid
erDiagram
    users {
        text id PK "UUID generated in Python"
        text full_name
        text email UK
        text password_hash "Argon2id"
        text phone
        text date_of_birth "ISO date"
        text currency "INR default"
        text avatar_path "Local file path"
        text master_password_hash "Argon2id for vault"
        text master_password_salt "Hex 32-byte salt"
        text security_question "For local password recovery"
        text security_answer_hash "Argon2id hash"
        integer is_setup_complete "0 or 1"
        integer is_active "0 or 1"
        text last_login_at "ISO timestamp"
        text created_at
        text updated_at
    }

    user_sessions {
        text id PK
        text user_id FK
        text session_token_hash "SHA-256"
        text ip_address
        text expires_at
        integer is_revoked "0 or 1"
        text created_at
    }

    user_preferences {
        text id PK
        text user_id FK "one-to-one"
        integer dark_mode "0 or 1"
        text date_format "DD/MM/YYYY"
        text number_format "en-IN"
        integer sip_reminders "0 or 1"
        integer sip_reminder_days "default 3"
        text portfolio_alert_freq "weekly"
        integer benchmark_alerts "0 or 1"
        integer vault_inactivity_reminder "0 or 1"
        integer auto_lock_minutes "default 15"
        text created_at
        text updated_at
    }

    asset_types {
        text id PK "Short IDs: at_mf, at_eq"
        text name UK "Mutual Fund, Equity, etc."
        text slug UK
        text icon
        integer sort_order
        integer is_active "0 or 1"
    }

    assets {
        text id PK
        text user_id FK
        text asset_type_id FK
        text name
        text serial_number
        integer invested_amount "PAISE: 123456 = Rs 1234.56"
        integer current_value "PAISE"
        text purchase_date "ISO date"
        text notes
        integer is_guaranteed "0 or 1"
        real guaranteed_return_pct "8.5 percent"
        text maturity_date
        text created_at
        text updated_at
    }

    asset_images {
        text id PK
        text asset_id FK
        text file_path "Relative to storage dir"
        text file_name
        text mime_type
        integer file_size_bytes
        text created_at
    }

    sip_schedules {
        text id PK
        text asset_id FK
        text user_id FK
        integer amount "PAISE"
        text frequency "monthly or quarterly"
        text start_date
        text end_date "nullable"
        text next_due_date
        text status "active, paused, completed"
        integer auto_update_value "0 or 1"
        text created_at
        text updated_at
    }

    asset_price_history {
        text id PK
        text asset_id FK
        integer value "PAISE"
        text recorded_date
        text source "manual or sip"
        text created_at
    }

    expense_categories {
        text id PK "Short IDs: ec_food, ec_transport"
        text user_id FK "NULL for system defaults"
        text name
        text slug
        text color_hex
        text icon
        integer sort_order
        integer is_active "0 or 1"
        integer is_system "0 or 1"
        text created_at
        text updated_at
    }

    household_members {
        text id PK
        text user_id FK
        text name
        text relationship "Self, Spouse, Parent, Child"
        text avatar_initial
        integer is_active "0 or 1"
        text created_at
        text updated_at
    }

    expenses {
        text id PK
        text user_id FK
        text category_id FK
        text spent_by_id FK "household_members"
        text spent_for_id FK "household_members, nullable"
        text expense_date "ISO date"
        integer amount "PAISE"
        text description
        text notes
        text created_at
        text updated_at
    }

    vault_credential_categories {
        text id PK "Short IDs: vc_social, vc_finance"
        text name "Social, Finance, Work, Shopping, Other"
        text slug
        integer sort_order
    }

    vault_credentials {
        text id PK
        text user_id FK
        text category_id FK "nullable"
        text service_name_enc "AES-256-CBC encrypted"
        text url_enc "AES-256-CBC encrypted"
        text username_enc "AES-256-CBC encrypted"
        text password_enc "AES-256-CBC encrypted"
        text notes_enc "AES-256-CBC encrypted"
        text favicon_url "Not encrypted"
        text last_password_changed
        text created_at
        text updated_at
    }

    vault_audit_log {
        text id PK
        text user_id FK
        text action "unlock, lock, view, copy, create, delete, export"
        text credential_id FK "nullable"
        text ip_address
        text created_at
    }

    notifications {
        text id PK
        text user_id FK
        text type "sip_reminder, portfolio_alert, system"
        text title
        text message
        text icon
        text action_url "nullable"
        integer is_read "0 or 1"
        text read_at
        text created_at
    }

    report_exports {
        text id PK
        text user_id FK
        text format "pptx, csv, json, pdf"
        text status "completed always for standalone"
        text file_path "Relative to exports dir"
        text included_sections "JSON array as text"
        text date_from
        text date_to
        text created_at
    }

    benchmark_data {
        text id PK
        text benchmark_name "Nifty50, Sensex, GoldRate"
        text recorded_date
        real value
        real return_pct
        text period "1M, 3M, 6M, 1Y"
        text created_at
    }

    audit_log {
        text id PK
        text user_id FK "nullable"
        text event_type "auth.login, data.export, etc."
        text entity_type
        text entity_id
        text metadata "JSON as text"
        text created_at
    }

    %% ===== RELATIONSHIPS =====

    users ||--o{ user_sessions : "has many"
    users ||--|| user_preferences : "has one"
    users ||--o{ assets : "owns many"
    users ||--o{ sip_schedules : "configures many"
    users ||--o{ expenses : "logs many"
    users ||--o{ expense_categories : "customizes"
    users ||--o{ household_members : "defines"
    users ||--o{ vault_credentials : "stores many"
    users ||--o{ vault_audit_log : "generates"
    users ||--o{ notifications : "receives"
    users ||--o{ report_exports : "requests"
    users ||--o{ audit_log : "triggers"

    asset_types ||--o{ assets : "classifies"
    assets ||--o{ asset_images : "has many"
    assets ||--o{ sip_schedules : "has SIP"
    assets ||--o{ asset_price_history : "tracks"

    expense_categories ||--o{ expenses : "categorizes"
    household_members ||--o{ expenses : "spent_by"

    vault_credential_categories ||--o{ vault_credentials : "tags"
    vault_credentials ||--o{ vault_audit_log : "audited"
```

---

## 2. Relationship Summary Table

| Parent Table | Child Table | Relationship | FK Column | ON DELETE |
|---|---|---|---|---|
| users | user_sessions | 1:N | user_id | CASCADE |
| users | user_preferences | 1:1 | user_id | CASCADE |
| users | assets | 1:N | user_id | CASCADE |
| users | sip_schedules | 1:N | user_id | CASCADE |
| users | expenses | 1:N | user_id | CASCADE |
| users | expense_categories | 1:N | user_id | SET NULL |
| users | household_members | 1:N | user_id | CASCADE |
| users | vault_credentials | 1:N | user_id | CASCADE |
| users | vault_audit_log | 1:N | user_id | CASCADE |
| users | notifications | 1:N | user_id | CASCADE |
| users | report_exports | 1:N | user_id | CASCADE |
| users | audit_log | 1:N | user_id | SET NULL |
| asset_types | assets | 1:N | asset_type_id | RESTRICT |
| assets | asset_images | 1:N | asset_id | CASCADE |
| assets | sip_schedules | 1:N | asset_id | CASCADE |
| assets | asset_price_history | 1:N | asset_id | CASCADE |
| expense_categories | expenses | 1:N | category_id | RESTRICT |
| household_members | expenses | 1:N | spent_by_id | RESTRICT |
| household_members | expenses | 1:N | spent_for_id | SET NULL |
| vault_credential_categories | vault_credentials | 1:N | category_id | SET NULL |
| vault_credentials | vault_audit_log | 1:N | credential_id | SET NULL |

### Key differences from PostgreSQL version:
- **Removed**: `password_reset_tokens` table (replaced by security question on `users`)
- **Removed**: `background_jobs` table (APScheduler is in-memory, no DB tracking)
- **Changed**: All `uuid` → `text`, all `decimal` → `integer` (paise), all `timestamp` → `text`
- **Total tables**: 18 (was 20)

---

## 3. Standalone Architecture Block Diagram

```mermaid
graph TB
    subgraph "User's Machine"
        BROWSER["🌐 Browser<br/>http://localhost:8000"]

        subgraph "FinVault Process (single Python process)"
            direction TB

            STATIC["📁 Jinja2 Templates<br/>Server-rendered HTML<br/>HTMX + Alpine.js + Chart.js"]

            subgraph "FastAPI Application"
                direction TB
                AUTH_MW["🔐 Auth Middleware<br/>Session token verification"]

                subgraph "API Routers"
                    R1["📋 /auth"]
                    R2["📋 /users"]
                    R3["📋 /assets"]
                    R4["📋 /expenses"]
                    R5["📋 /vault"]
                    R6["📋 /reports"]
                    R7["📋 /settings"]
                    R8["📋 /notifications"]
                end

                subgraph "Service Layer"
                    S1["AuthService"]
                    S2["AssetService"]
                    S3["ExpenseService"]
                    S4["VaultService"]
                    S5["ReportService"]
                    S6["BackupService"]
                end

                subgraph "Repository Layer"
                    D1["UserRepo"]
                    D2["AssetRepo"]
                    D3["ExpenseRepo"]
                    D4["VaultRepo"]
                    D5["ReportRepo"]
                end

                subgraph "Crypto"
                    U1["AES-256-CBC<br/>Vault Encryption"]
                    U2["Argon2id<br/>Password Hashing"]
                    U3["PBKDF2-SHA256<br/>Key Derivation"]
                end
            end

            SCHED["⏰ APScheduler<br/>In-process cron jobs<br/>SIP reminders<br/>Auto-backup<br/>Cleanup"]
            CACHE["💾 TTLCache<br/>In-memory cache<br/>Portfolio summary<br/>Expense totals"]
        end

        subgraph "Local Filesystem (~/.finvault/)"
            SQLITE["🗄️ SQLite 3<br/>finvault.db<br/>WAL mode<br/>PRAGMA foreign_keys=ON"]
            STORAGE["📂 storage/<br/>avatars/<br/>asset-images/<br/>exports/"]
            BACKUPS["💾 backups/<br/>finvault_YYYY-MM-DD.db"]
            LOGS["📝 logs/<br/>finvault.log"]
        end

        BROWSER --> STATIC
        BROWSER --> AUTH_MW
        AUTH_MW --> R1 & R2 & R3 & R4 & R5 & R6 & R7 & R8
        R1 --> S1
        R3 --> S2
        R4 --> S3
        R5 --> S4
        R6 --> S5
        R7 --> S6
        S1 --> D1
        S2 --> D2
        S3 --> D3
        S4 --> D4
        S5 --> D5
        S4 --> U1
        S1 --> U2
        S4 --> U3
        D1 & D2 & D3 & D4 & D5 --> SQLITE
        S2 & S6 --> STORAGE
        S6 --> BACKUPS
        SCHED --> SQLITE
    end
```

---

## 4. Application Layer Detail

```mermaid
graph TB
    subgraph "FastAPI Application"
        direction TB

        subgraph "Middleware Stack (simplified)"
            M1["RequestLoggingMiddleware"]
            M2["SessionAuthMiddleware"]
            M3["AutoLockMiddleware<br/>Invalidate after N min inactivity"]
            M1 --> M2 --> M3
        end

        subgraph "API Routers"
            R1["📋 /api/v1/auth<br/>login, logout, change-pw,<br/>reset-pw-local"]
            R2["📋 /api/v1/users<br/>profile, preferences,<br/>setup wizard"]
            R3["📋 /api/v1/assets<br/>CRUD, images, bulk,<br/>SIP schedules"]
            R4["📋 /api/v1/expenses<br/>CRUD, calendar,<br/>categories, household"]
            R5["📋 /api/v1/vault<br/>unlock, lock, CRUD,<br/>generate pw, export"]
            R6["📋 /api/v1/reports<br/>portfolio, health,<br/>benchmark, export"]
            R7["📋 /api/v1/settings<br/>backup, restore,<br/>import, export, reset"]
            R8["📋 /api/v1/notifications<br/>list, count, mark read"]
        end

        subgraph "Service Layer"
            S1["AuthService<br/>Session token management"]
            S2["UserService<br/>Profile, setup wizard"]
            S3["AssetService<br/>P/L computation in Python"]
            S4["ExpenseService<br/>Calendar aggregation"]
            S5["VaultService<br/>AES encrypt/decrypt"]
            S6["ReportService<br/>Sync PowerPoint generation"]
            S7["NotificationService"]
            S8["BackupService<br/>DB file copy/restore"]
            S9["FileStorageService<br/>Local filesystem ops"]
        end

        subgraph "Repository Layer (DAL)"
            D1["UserRepository"]
            D2["AssetRepository"]
            D3["ExpenseRepository"]
            D4["VaultRepository"]
            D5["ReportRepository"]
            D6["NotificationRepository"]
        end

        subgraph "Shared Utilities"
            U1["crypto/vault.py<br/>AES-256-CBC"]
            U2["crypto/hashing.py<br/>Argon2id"]
            U3["crypto/session.py<br/>Token + auto-lock"]
            U4["utils/currency.py<br/>Paise to Rupees"]
            U5["utils/paths.py<br/>App data dir resolution"]
        end

        M3 --> R1 & R2 & R3 & R4 & R5 & R6 & R7 & R8
        R1 --> S1
        R2 --> S2
        R3 --> S3
        R4 --> S4
        R5 --> S5
        R6 --> S6
        R7 --> S8
        R8 --> S7
        S1 --> D1
        S3 --> D2
        S4 --> D3
        S5 --> D4
        S6 --> D5
        S7 --> D6
        S5 --> U1
        S1 --> U2
        S3 --> U4
        S4 --> U4
    end
```

---

## 5. Data Flow Diagrams

### 5.1 — Authentication Flow (Standalone)

```mermaid
sequenceDiagram
    participant C as Browser
    participant API as FastAPI (localhost)
    participant DB as SQLite

    C->>API: POST /api/v1/auth/login {email, password}
    API->>DB: SELECT user WHERE email = ?
    DB-->>API: user row
    API->>API: Argon2id verify(password, hash)
    alt Correct Password
        API->>API: Generate session_token (secrets.token_urlsafe)
        API->>DB: INSERT user_sessions (session_token_hash)
        API->>DB: UPDATE users SET last_login_at = now
        API-->>C: 200 {user, session_token}
        Note over C: Token stored in localStorage
    else Wrong Password
        API->>DB: INSERT audit_log (event='auth.login_failed')
        API-->>C: 401 {error: 'Invalid credentials'}
    end

    C->>API: GET /api/v1/assets (Header: Bearer session_token)
    API->>API: SHA-256(token) → lookup in sessions table
    API->>API: Check auto-lock timer (last activity)
    API->>DB: SELECT assets WHERE user_id = ?
    DB-->>API: asset rows
    API-->>C: 200 {data: [...]}
```

### 5.2 — Vault Unlock & Credential Retrieval (Standalone)

```mermaid
sequenceDiagram
    participant C as Browser
    participant API as FastAPI (localhost)
    participant MEM as In-Memory Cache
    participant DB as SQLite

    C->>API: POST /api/v1/vault/unlock {master_password}
    API->>DB: SELECT master_password_hash, salt FROM users
    DB-->>API: hash + salt
    API->>API: Argon2id verify(master_password, stored_hash)
    alt Correct Password
        API->>API: PBKDF2-SHA256 derive_key(master_password, salt)
        API->>MEM: Store vault_key in memory (TTL=15min)
        API->>DB: INSERT vault_audit_log (action='unlock')
        API-->>C: 200 {vault_unlocked: true, expires_in: 900}
    else Wrong Password
        API->>DB: INSERT vault_audit_log (action='unlock_failed')
        API-->>C: 401 {error: 'Invalid master password'}
    end

    C->>API: GET /api/v1/vault/credentials
    API->>MEM: Get vault_key from memory
    MEM-->>API: encryption_key
    API->>DB: SELECT * FROM vault_credentials WHERE user_id = ?
    DB-->>API: encrypted credential rows
    API->>API: AES-256-CBC decrypt each field with key
    API-->>C: 200 {data: [decrypted credentials]}
```

### 5.3 — Report Export Flow (Synchronous)

```mermaid
sequenceDiagram
    participant C as Browser
    participant API as FastAPI (localhost)
    participant DB as SQLite
    participant FS as Local Filesystem

    C->>API: POST /api/v1/reports/export {sections, format, date_range}
    API->>DB: SELECT assets, expenses, benchmarks WHERE user_id
    DB-->>API: all data rows
    API->>API: Generate matplotlib charts as PNG buffers
    API->>API: Build python-pptx slides with data + charts
    API->>FS: Save to ~/.finvault/storage/exports/report_2025-06-10.pptx
    API->>DB: INSERT report_exports (status='completed', file_path)
    API-->>C: FileResponse (direct download)
    Note over C: File downloads immediately. No polling needed.
```

### 5.4 — Backup & Restore Flow

```mermaid
sequenceDiagram
    participant C as Browser
    participant API as FastAPI (localhost)
    participant DB as SQLite
    participant FS as Local Filesystem

    Note over C,FS: Manual Backup
    C->>API: POST /api/v1/settings/backup
    API->>FS: shutil.copy2(finvault.db → backups/finvault_2025-06-10.db)
    API-->>C: 200 {backup_file: "finvault_2025-06-10_143000.db", size: "2.4 MB"}

    Note over C,FS: Restore from Backup
    C->>API: POST /api/v1/settings/restore {filename: "finvault_2025-06-10.db"}
    API->>FS: Verify backup file exists
    API->>FS: Copy current DB to backups/pre_restore_<timestamp>.db
    API->>DB: Close all connections
    API->>FS: Replace finvault.db with backup file
    API->>DB: Reconnect, run integrity check
    API-->>C: 200 {message: "Restored successfully", pre_restore_backup: "..."}
```

---

## 6. Security Architecture (Standalone)

```mermaid
graph TB
    subgraph "Defense Layers (Localhost)"
        direction TB
        L1["Layer 1: Localhost Binding<br/>127.0.0.1 only<br/>Not accessible from network"]
        L2["Layer 2: Authentication<br/>Session token (secrets.token_urlsafe)<br/>Auto-lock after inactivity"]
        L3["Layer 3: Input Validation<br/>Pydantic schema validation<br/>SQLAlchemy parameterized queries"]
        L4["Layer 4: Master Password Gate<br/>Vault operations require<br/>separate master password<br/>Derived key cached 15min only"]
        L5["Layer 5: Data Encryption<br/>Argon2id password hashing<br/>AES-256-CBC vault encryption<br/>PBKDF2-SHA256 key derivation<br/>Per-credential random IV"]
        L6["Layer 6: Audit Trail<br/>All auth events logged<br/>All vault access logged<br/>All data operations logged"]
        L7["Layer 7: Data Isolation<br/>Single file on user's disk<br/>Backup = copy file<br/>Delete = delete file<br/>No cloud, no network"]

        L1 --> L2 --> L3 --> L4 --> L5 --> L6 --> L7
    end
```

---

## 7. Index Strategy (SQLite)

```mermaid
graph LR
    subgraph "Hot Tables (Frequent R/W)"
        T1["expenses<br/>idx: user_id + expense_date<br/>idx: user_id + category_id<br/>idx: spent_by_id"]
        T2["vault_credentials<br/>idx: user_id"]
        T3["notifications<br/>idx: user_id + is_read + created_at"]
    end

    subgraph "Warm Tables (Moderate R/W)"
        T4["assets<br/>idx: user_id<br/>idx: user_id + asset_type_id"]
        T5["sip_schedules<br/>idx: user_id<br/>idx: next_due_date"]
        T6["asset_price_history<br/>idx: asset_id + recorded_date"]
    end

    subgraph "Cold Tables (Append-mostly)"
        T7["audit_log<br/>idx: user_id + created_at"]
        T8["vault_audit_log<br/>idx: user_id + created_at"]
        T9["benchmark_data<br/>idx: benchmark_name + recorded_date"]
    end

    subgraph "FTS5 Virtual Tables"
        F1["assets_fts<br/>Searchable: name, serial_number, notes"]
        F2["expenses_fts<br/>Searchable: description, notes"]
    end
```

---

## 8. Build & Release Pipeline

```mermaid
graph LR
    subgraph "CI/CD Pipeline"
        A["Git Push<br/>or Tag v*"] --> B["GitHub Actions<br/>Trigger"]
        B --> C["Stage 1: Lint<br/>ruff + black + mypy"]
        C --> D["Stage 2: Test<br/>pytest + in-memory SQLite"]
        D --> E{"Is tag v*?"}
        E -->|No| F["✅ PR Checks Pass"]
        E -->|Yes| G["Stage 3: PyInstaller<br/>Bundle Python + deps<br/>+ templates + static"]
        G --> I["Stage 4: Package<br/>Windows: .zip<br/>Linux: .tar.gz"]
        I --> J["Stage 5: GitHub Release<br/>Upload artifacts<br/>Auto release notes"]
        J --> K["✅ Users Download"]
    end
```
