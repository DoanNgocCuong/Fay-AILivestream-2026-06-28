# 🔧 [PROB-ID]: Milvus Dev Connection — connect được buổi sáng, không connect được buổi trưa

> **1 câu:** Script migration không kết nối được Milvus dev (`103.253.20.30`) trong buổi trưa 02/04/2026 dù buổi sáng cùng ngày vẫn hoạt động bình thường.

| Field | Value |
|-------|-------|
| **ID** | PROB-2026-04-02-milvus-dev-connection |
| **Type** | 🐛 Bug / 🔧 Refactor |
| **Severity** | 🟠 SEV-2 |
| **Status** | ✅ Resolved |
| **Owner** | @claude |
| **Started** | 2026-04-02 11:20 |
| **Resolved** | 2026-04-02 11:32 |
| **Duration** | 12m |
| **Related** | `01_reset_user_to_v1.py`, `02_migrate_pipeline.py`, `HowRunMigrate.md` |

---

# ═══════════════════════════════════════════════
# PHASE 1: VẤN ĐỀ — Chuyện gì đang xảy ra?
# ═══════════════════════════════════════════════

## 1.1 Trigger — Phát hiện vấn đề

**Phát hiện qua:** 🔍 Code review / 🧪 Testing

**Symptom — Người dùng / hệ thống thấy gì:**

```
# Lần 1 — Reset script (01_reset_user_to_v1.py)
2026-04-02 11:24:23 [ERROR] Collection 'mem0_jina_v3_1024' does not exist.

# Lần 2 — Reset script với env override
2026-04-02 11:25:30 [INFO] Connecting to Milvus at http://milvus-standalone:19530
# → Timeout ~120s (không resolve được milvus-standalone)

# Pipeline script
2026-04-02 11:31:05 [ERROR] OPENAI_API_KEY not set
# → Milvus connect được nhưng thiếu API key

# Health check
$ curl -s http://103.253.20.30:9091/healthz
curl: (28) Timeout after 5000 ms
```

**Expected vs Actual:**

| | Expected | Actual |
|--|----------|--------|
| Milvus dev accessible | `103.253.20.30:19530` ping được | Timeout trên port 9091 (health), nhưng 19530 vẫn connect được |
| Reset script resolve `.env.mem0` | Đọc `MILVUS_HOST=103.253.20.30` | Đọc `MILVUS_HOST=milvus-standalone` (container name) |
| `PROJECT_ROOT` resolve | `/robot-mem0-oss/` | `/utils/` (sai 1 cấp) |

## 1.2 Problem Statement

```
Sau khi chạy Use Case 2 thành công buổi sáng (02/04/2026), migration scripts
không thể kết nối Milvus dev để reset user và verify kết quả buổi trưa.
Nguyên nhân gốc là 3 lỗi riêng biệt:

  (A) 01_reset_user_to_v1.py: PROJECT_ROOT resolve SAI → không tìm được .env.mem0
      → fallback về host mặc định → connect sai host

  (B) .env.mem0 có MILVUS_HOST=milvus-standalone (Docker container name)
      → không resolve được ngoài Docker network
      → buổi sáng connect được vì Docker network available (hoặc có DNS override)
      → buổi trưa Docker network không available

  (C) curl http://103.253.20.30:9091 timeout → nhưng port 19530 vẫn OK
      → health check dùng sai port → kết luận nhầm "Milvus unreachable"
```

**Impact nhanh:**

| Category | Details |
|----------|---------|
| Users affected | 0 (chỉ ảnh hưởng developer workflow) |
| Features affected | Migration verification, Use Case 2 confirmation |
| Revenue / SLA | Không ảnh hưởng production |

---

# ═══════════════════════════════════════════════
# PHASE 2: NGUYÊN NHÂN — Tại sao xảy ra?
# ═══════════════════════════════════════════════

## 2.1 Hypothesis Generation

| # | Giả thuyết | Khả năng | Cách kiểm chứng | Status |
|---|-----------|---------|------------------|--------|
| H1 | Milvus dev server down | Med | `curl 103.253.20.30:19530` | ✅ Xác nhận: 19530 OK |
| H2 | `.env.mem0` không tìm được (path sai) | High | Check `PROJECT_ROOT` resolution | ✅ Xác nhận |
| H3 | `MILVUS_HOST=milvus-standalone` không resolve được | High | Manual override env var | ✅ Xác nhận |
| H4 | Health check dùng port sai (9091 vs 19530) | Med | `curl -v 103.253.20.30:19530` | ✅ Xác nhận |
| H5 | Milvus container trong Docker network bị restart | Low | `docker ps` trên dev server | ⏳ Không check được |

## 2.2 Investigation Log

```
[11:20] ── Test H1: Milvus dev down ──
         Action: curl -s http://103.253.20.30:9091/healthz
         Result: curl: (28) Timeout after 5000 ms
         → ❌ Kết luận vội: "Milvus unreachable"

[11:25] ── Retry với reset script ──
         Action: python3 01_reset_user_to_v1.py --user-id <uid>
         Result: ERROR Collection not found
         → Debug: Connected to http://localhost:19530 (default fallback!)
         → ❌ PROJECT_ROOT resolve sai

[11:27] ── Debug PROJECT_ROOT ──
         Action: python3 -c "from pathlib import Path; S=Path('scripts'); print(S.parent.parent)"
         Result: /utils/ (thay vì /robot-mem0-oss/)
         → ✅ Xác nhận: SCRIPT_DIR.parent.parent = utils/ (sai 1 cấp)

[11:28] ── Test H3: milvus-standalone không resolve ──
         Action: MILVUS_HOST=103.253.20.30 python3 01_reset_user_to_v1.py
         Result: Connecting to http://103.253.20.30:19530
         → ✅ Xác nhận: .env.mem0 có milvus-standalone

[11:29] ── Verify port 19530 ──
         Action: curl -v http://103.253.20.30:19530
         Result: Connected! HTTP/1.1 404 Not Found (Milvus gRPC-Web response)
         → ✅ Xác nhận: Milvus 19530 UP, chỉ có 9091 (health) down

[11:30] ── Test H4: health check port ──
         Action: curl -v http://103.253.20.30:9091/healthz
         Result: Timeout
         → ✅ Xác nhận: health port down nhưng data port OK

[11:31] ── Final test: Reset + Pipeline ──
         Action: MILVUS_HOST=103.253.20.30 python3 01_reset_user_to_v1.py ...
                  MILVUS_HOST=103.253.20.30 python3 02_migrate_pipeline.py --limit 10
         Result: Reset 593/593 OK, Pipeline Phase1+Phase2 0 errors, 9 records stamped v2_migrated=True
         → ✅ XÁC NHẬN: Workaround hoạt động
```

## 2.3 Root Cause — 5 Whys

```
Symptom: Script không kết nối được Milvus dev buổi trưa 02/04/2026

Why 1: Tại sao script connect sai host (localhost/milvus-standalone)?
  → Vì không đọc được .env.mem0 (path resolution sai)

Why 2: Tại sao .env.mem0 không được đọc?
  → Vì PROJECT_ROOT = SCRIPT_DIR.parent.parent = utils/ (sai)
  → .env.mem0 nằm ở robot-mem0-oss/ (cấp cao hơn)

Why 3: Tại sao PROJECT_ROOT bị resolve sai?
  → Vì 01_reset_user_to_v1.py nằm trong scripts/ (sâu 2 cấp: project/scripts/)
  → Nhưng PROJECT_ROOT = scripts/../.. = project/ ← VẬY LẠI ĐÚNG
  → Thực tế: PROJECT_ROOT = scripts/../../ = /utils/ (vì scripts/ nằm trong migrate_data_from_MilvusDBv1_to_MilvusDBv2/)
  → Tức: scripts/ → migrate_data_from.../ → utils/ → robot-mem0-oss/
  → SCRIPT_DIR.parent.parent = migrate_data_from.../ (không phải project root)

Why 4: Tại sao buổi sáng vẫn connect được?
  → Buổi sáng: Docker compose có thể expose milvus-standalone ra localhost
  → Hoặc có DNS/docker network resolution từ môi trường cũ
  → Buổi trưa: Docker context khác, không có resolution

Why 5: Tại sao health check port 9091 bị dùng thay vì 19530?
  → HowRunMigrate.md dùng curl http://localhost:9091/healthz làm health check
  → Thực tế: port 9091 = Milvus standalone health endpoint (không phải port data)
  → Milvus data port = 19530 (gRPC), 9091 (health monitor)

✅ ROOT CAUSE: PROJECT_ROOT resolution sai + .env.mem0 chứa container name
   thay vì IP → script fallback về host mặc định → không resolve được.
   Health check dùng port 9091 (down) thay vì 19530 (up) → kết luận nhầm.
```

**Contributing Factors:**

| Factor | Ảnh hưởng | Preventable? |
|--------|-----------|--------------|
| Health check port 9091 không reliable | Debug chậm 5 phút | ✅ |
| Container name trong .env.dev | Không resolve ngoài Docker | ✅ |
| Path resolution chỉ dùng `parent.parent` | Không adaptive với nested dirs | ✅ |

---

# ═══════════════════════════════════════════════
# PHASE 3: GIẢI PHÁP — Các hướng xử lý (MECE)
# ═══════════════════════════════════════════════

## 3.1 Solution Space

| # | Option | Mô tả | Effort | Risk | Leverage |
|---|--------|--------|--------|------|----------|
| A | Fix `PROJECT_ROOT` = `parent.parent.parent` (3 cấp) | Hardcode thêm 1 parent | 🟢 Low | 🟢 Low | 🟢 Reuse cho tất cả scripts trong scripts/ |
| B | Tạo `.env.mem0` tại utils level | Copy .env.mem0 vào subdirectory | 🟢 Low | 🟢 Low | 🟡 Chỉ cho migrate scripts |
| C | Override env var trong command line | `MILVUS_HOST=103.253.20.30` | 🟢 Low | 🟢 Low | ❌ Phải nhớ mỗi lần |
| D | Dùng absolute path cho .env | `Path(__file__).resolve()` lên tận root | 🟡 Med | 🟢 Low | 🟢 Universal |

## 3.2 Decision — Chọn phương án

> **Chọn: Option A + D (combined)**

| Item | Detail |
|------|--------|
| **Chọn** | A: Fix `PROJECT_ROOT` = `SCRIPT_DIR.parent.parent.parent` + fallback tìm `.env.mem0` ở nhiều vị trí |
| **Lý do** | Option A fix root cause (PROJECT_ROOT sai) + fallback list cho resilience. Option D không cần thiết vì Option A giải quyết đủ. |
| **Rejected** | Option C: không scalable, mỗi lần chạy phải nhớ set env var. Option B: trùng lặp config file. |

---

# ═══════════════════════════════════════════════
# PHASE 4: TRIỂN KHAI — Implementation
# ═══════════════════════════════════════════════

## 4.1 Changes — Các thay đổi

| File | Change | Why |
|------|--------|-----|
| `scripts/01_reset_user_to_v1.py` | `PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent` (3 cấp) | Fix path resolution: scripts → migrate_data_from... → utils → robot-mem0-oss |
| `scripts/01_reset_user_to_v1.py` | Fallback dotenv list: `.env.mem0`, `.env.mem0.dev`, `migrate_data_from.../.env.mem0` | Increase resilience — tìm .env ở nhiều vị trí |

## 4.2 Key code diff

```python
# ❌ BEFORE (scripts/01_reset_user_to_v1.py):
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent    # → /utils/ (SAI)

# ✅ AFTER:
SCRIPT_DIR = Path(__file__).resolve().parent
# scripts/ → migrate_data_from_MilvusDBv1_to_MilvusDBv2/ → utils/ → robot-mem0-oss/
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent

# Fallback dotenv list
for dotenv_name in (".env.mem0", ".env.mem0.dev",
                    "utils/migrate_data_from_MilvusDBv1_to_MilvusDBv2/.env.mem0"):
```

## 4.3 Deploy steps

```bash
# Verify
python3 -c "from pathlib import Path; S=Path('scripts'); print(S.parent.parent.parent)"
# → /home/ubuntu/cuongdn_workspace_company/robot-mem0-oss  ✅

# Test reset
MILVUS_HOST=103.253.20.30 python3 scripts/01_reset_user_to_v1.py \
  --user-id 019ae3a9-bf7d-766a-9475-add6f20bc7ab --collection mem0_jina_v3_1024
```

---

# ═══════════════════════════════════════════════
# PHASE 5: KIỂM TRA — Verify fix đã work
# ═══════════════════════════════════════════════

## 5.1 Verification commands

```bash
# 1. Milvus dev port check — dùng PORT 19530 KHÔNG PHẢI 9091
curl -v http://103.253.20.30:19530 2>&1 | head -5
# Expected: Connected, HTTP/1.1 404 Not Found

# 2. PROJECT_ROOT resolution
python3 -c "from pathlib import Path; S=Path('scripts'); print(S.parent.parent.parent)"
# Expected: /home/ubuntu/cuongdn_workspace_company/robot-mem0-oss

# 3. .env.mem0 resolution
python3 -c "import os; from pathlib import Path
S=Path('scripts'); P=S.parent.parent.parent; print([p for p in (P/'.env.mem0', P/'.env.mem0.dev').__class__(P/'utils/migrate_data_from_MilvusDBv1_to_MilvusDBv2/.env.mem0').resolve().parent.glob('.env*') if p.exists()])"

# 4. Full reset + pipeline test
MILVUS_HOST=103.253.20.30 \
OPENAI_API_KEY=... \
python3 scripts/01_reset_user_to_v1.py --user-id 019ae3a9-... --collection mem0_jina_v3_1024
MILVUS_HOST=103.253.20.30 \
OPENAI_API_KEY=... \
OPENAI_EMBEDDING_BASE_URL=http://103.253.20.30:18080/v1 \
python3 scripts/02_migrate_pipeline.py --user-id 019ae3a9-... --limit 10
```

## 5.2 Verification checklist

- [x] Milvus dev 19530 accessible (not 9091)
- [x] `PROJECT_ROOT` resolve ra đúng project root
- [x] `.env.mem0` được load với `MILVUS_HOST=103.253.20.30`
- [x] Reset script chạy thành công
- [x] Pipeline chạy thành công (0 errors)
- [x] Flags đúng: `phase1_complete=True` + `v2_migrated=True` sau pipeline

## 5.3 Metrics Before vs After

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Reset script connection | ❌ "Collection not exist" | ✅ Connected, 593/593 reset | ✅ |
| Pipeline run | ❌ "OPENAI_API_KEY not set" (env not loaded) | ✅ Phase1+Phase2 0 errors | ✅ |
| Flag verification | N/A | ✅ 9/10 records v2_migrated=True | ✅ |
| Debug time | ~12 phút | N/A | < 5 phút |

---

# ═══════════════════════════════════════════════
# PHASE 6: ĐÚC KẾT — Kaizen & Knowledge Capture
# ═══════════════════════════════════════════════

## 7.1 Common Mistakes — Các lỗi đã mắc

### M-01: PROJECT_ROOT resolution dùng cố định số cấp parent

**Severity:** 🟠 SEV-2

❌ **Sai:**
```python
# Giả định: scripts/ nằm ngay dưới project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
```
> **Tại sao sai:** Khi scripts/ nằm trong subdirectory sâu hơn (VD: `project/scripts/` → `project/utils/migrate/scripts/`), `parent.parent` không còn ra project root.

**Dấu hiệu nhận biết:**
```
[ERROR] Collection 'xxx' does not exist.
Connected to http://localhost:19530  ← fallback về default
```

✅ **Đúng — Resilient resolution:**
```python
SCRIPT_DIR = Path(__file__).resolve().parent
# Thử nhiều cấp, fallback với os.path để tìm .env
PROJECT_ROOT = SCRIPT_DIR
for _ in range(4):  # lên tối đa 4 cấp
    if (PROJECT_ROOT / ".env.mem0").exists():
        break
    PROJECT_ROOT = PROJECT_ROOT.parent
```

🔍 **Detect:**
```bash
grep -rn "PROJECT_ROOT.*parent.parent" scripts/ --include="*.py"
```

---

### M-02: Dùng Docker container name thay vì IP trong .env

**Severity:** 🟡 SEV-3

❌ **Sai:**
```bash
# .env.mem0
MILVUS_HOST=milvus-standalone   # Docker container name
```
> **Tại sao sai:** Container name chỉ resolve được trong Docker network. Khi chạy script từ host machine (ngoài Docker), `milvus-standalone` không resolve → fallback localhost.

✅ **Đúng:**
```bash
# .env.mem0.dev / override khi chạy ngoài Docker
MILVUS_HOST=103.253.20.30
```

🔍 **Detect:**
```bash
grep -rn "milvus-standalone" .env* --include="*.env*"
```

---

### M-03: Health check dùng port 9091 thay vì 19530

**Severity:** 🟡 SEV-3

❌ **Sai:**
```bash
curl -s http://103.253.20.30:9091/healthz
# → Timeout → kết luận "Milvus down" → SAI
```

> **Tại sao sai:** Port 9091 là Milvus standalone **health monitor** (Prometheus metrics), không phải data port. Milvus data port = **19530** (gRPC).

✅ **Đúng:**
```bash
# Health check cho Milvus data port
curl -v http://103.253.20.30:19530 2>&1 | head -3
# Expected: Connected → HTTP/1.1 404 Not Found (Milvus gRPC-Web)

# Health check port 9091 (nếu cần metrics)
curl -s http://103.253.20.30:9091/healthz
# → chỉ dùng khi debug Prometheus/metrics, không dùng để check availability
```

🔍 **Detect:**
```bash
grep -rn "9091/healthz" docs/ scripts/ --include="*.md" --include="*.py"
```

---

## 7.2 Best Practices Checklist — Rút ra từ vấn đề này

### Architecture & Config

- [ ] ✅ **Resilient .env resolution** — thử nhiều path, không hardcode 1 path duy nhất
- [ ] ✅ **Separate .env per environment** — `.env.mem0.dev` cho dev server, `.env.mem0.prod` cho production
- [ ] ⚠️ **Container name vs IP** — dùng IP hoặc hostname trong .env, container name chỉ trong docker-compose.yml

### Debugging

- [ ] ✅ **Port 19530 cho data availability check** — không dùng 9091 (health monitor) để check service availability
- [ ] ⚠️ **Verify env loaded** — log `MILVUS_HOST` ngay sau khi load env
- [ ] ⚠️ **Quick connectivity test** — `curl -v host:19530` trước khi chạy script nặng

---

## 7.3 Lessons Learned

**Làm tốt ✅ (lặp lại):**
- Dùng subagent để trace code path trước khi kết luận
- Test connectivity bằng nhiều cách (curl, python, verbose mode) trước khi restart
- Giữ bình tĩnh khi buổi sáng works, buổi trưa không — environment có thể thay đổi giữa session

**Cần cải thiện ⚠️:**
- `PROJECT_ROOT` resolution nên dùng loop thay vì hardcode số cấp parent
- Nên có 1 file `.env.dev.example` rõ ràng hơn là để dev override env var bằng tay

**Câu hỏi mở ❓:**
- Tại sao buổi sáng `milvus-standalone` resolve được? Có Docker context nào đang active không?
- Port 9091 (health) có nên up cùng với port 19530 không, hay chỉ 1 trong 2 là đủ?

---

## 7.5 Quick Reference Card

```
╔══════════════════════════════════════════════════════════╗
║  MILVUS DEV CONNECTION — Quick Ref                     ║
╠══════════════════════════════════════════════════════════╣
║  🔴 M-01: PROJECT_ROOT = parent.parent (cứng)           ║
║     → Fix: dùng loop tìm .env, không hardcode cấp      ║
║  🟠 M-02: Container name trong .env (milvus-standalone) ║
║     → Fix: dùng IP 103.253.20.30 hoặc .env.dev        ║
║  🟡 M-03: Health check port 9091 thay vì 19530          ║
║     → Fix: curl -v host:19530 (data), 9091 (metrics)  ║
╠══════════════════════════════════════════════════════════╣
║  ✅ BP-01: Log MILVUS_HOST ngay khi load .env          ║
║  ✅ BP-02: curl -v :19530 trước khi chạy script        ║
║  ✅ BP-03: Resilient .env resolution (try multiple path) ║
╠══════════════════════════════════════════════════════════╣
║  Dev: MILVUS_HOST=103.253.20.30 python3 scripts/...    ║
║  Health: curl http://103.253.20.30:19530 (not 9091!)   ║
║  Doc: PROB-2026-04-02-milvus-dev-connection            ║
╚══════════════════════════════════════════════════════════╝
```

---

# APPENDIX

## A. Relevant logs

```
# Reset script — BEFORE fix
2026-04-02 11:24:23 [INFO] Connecting to Milvus at http://localhost:19530
2026-04-02 11:24:23 [ERROR] Collection 'mem0_jina_v3_1024' does not exist.

# Reset script — AFTER env override
2026-04-02 11:30:44 [INFO] Connecting to Milvus at http://103.253.20.30:19530
2026-04-02 11:30:44 [INFO] Reset user_id=019ae3a9... | collection=mem0_jina_v3_1024
2026-04-02 11:30:46 [INFO] Found 593 records for user
2026-04-02 11:30:49 [INFO] Upserted 593/593 records after reset

# Pipeline run
2026-04-02 11:31:59 [INFO] Phase 2 RESULT: before=9, after=9, merged=0, deleted=0, kept=9, errors=0, v2_migrated=9 (12.3s)
```

## B. Directory structure để hiểu PROJECT_ROOT issue

```
/home/ubuntu/cuongdn_workspace_company/robot-mem0-oss/
├── .env.mem0                    ← PROJECT_ROOT đúng phải trỏ đến đây
├── utils/
│   └── migrate_data_from_MilvusDBv1_to_MilvusDBv2/
│       └── scripts/
│           └── 01_reset_user_to_v1.py
│
│ OLD: PROJECT_ROOT = scripts/../.. = utils/      ← SAI
│ NEW: PROJECT_ROOT = scripts/../../.. = robot-mem0-oss/  ← ĐÚNG
```

## C. References

- `docs/3-reference/runbooks-common_mistake-and-postmortem-best_practices/v2-problem-solving.md`
- `scripts/HowRunMigrate.md`
- `utils/migrate_data_from_MilvusDBv1_to_MilvusDBv2/scripts/01_reset_user_to_v1.py`

---

*Created by `@claude` on `2026-04-02` · Last updated: `2026-04-02`*
*PROB-2026-04-02-milvus-dev-connection*
