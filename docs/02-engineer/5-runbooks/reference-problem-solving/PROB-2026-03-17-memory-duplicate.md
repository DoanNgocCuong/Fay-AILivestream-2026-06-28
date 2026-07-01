# 🔧 [PROB-ID]: Memory Duplicate - 29.4% memories bị trùng lặp

> **1 câu:** Hệ thống mem0 đang lưu trùng lặp ~30% memories do logic deduplicate không hiệu quả, dẫn đến tên user "Thảo My" bị lưu 124 lần.

| Field | Value |
|-------|-------|
| **ID** | PROB-2026-03-17-memory-duplicate |
| **Type** | 🐛 Bug |
| **Severity** | 🟠 SEV-2 |
| **Status** | 🔍 Investigating → 🧪 Experimenting → 🛠️ Implementing → ✅ Resolved |
| **Owner** | @cuong |
| **Started** | 2026-03-17 17:40 |
| **Resolved** | YYYY-MM-DD HH:MM |
| **Duration** | Xh Ym |
| **Related** | [scripts/mem0_export_50_users_20260316_160255/](scripts/mem0_export_50_users_20260316_160255/) |

---

# ═══════════════════════════════════════════════
# PHASE 1: VẤN ĐỀ — Chuyện gì đang xảy ra?
# ═══════════════════════════════════════════════

> _"Định nghĩa đúng vấn đề = giải quyết 50% vấn đề."_
> _Giải quyết triệu chứng ≠ Giải quyết nguyên nhân._

## 1.1 Trigger — Phát hiện vấn đề

**Phát hiện qua:** [ ] Alert / [ ] User report / [ ] Monitoring / [ ] Code review / [x] Testing / [ ] Tự phát hiện

**Symptom — Người dùng / hệ thống thấy gì:**

```
Export 50 users từ mem0 production → Phát hiện user "019b1b30" có 633 memories
→ Đếm số unique memories: 447
→ Số memories bị trùng: 186 (29.4%)
→ Memory "User's name is Thảo My" xuất hiện 124 LẦN!
```

**Expected vs Actual:**

| | Expected | Actual |
|--|----------|--------|
| Behavior | Mỗi fact unique chỉ lưu 1 lần | Cùng 1 fact lưu nhiều lần (124 lần) |
| Metric | Tỷ lệ trùng < 1% | Tỷ lệ trùng 29.4% |

**Reproduce steps:**

```bash
# Step 1: Export memories của 1 user
cd /home/ubuntu/cuong_dn/robot-mem0-oss/scripts/
python3 export_mem0_users.py --user_id 019b1b30-6579-74ba-ace2-51e39d116cdf

# Step 2: Load và đếm duplicates
python3 -c "
import json
from collections import Counter
with open('019b1b30-6579-74ba-ace2-51e39d116cdf.json') as f:
    data = json.load(f)
mem_counts = Counter([m['memory'] for m in data])
print(f'Total: {len(data)}, Unique: {len(mem_counts)}, Duplicates: {len(data)-len(mem_counts)}')
print('Top duplicates:', mem_counts.most_common(5))
"
# → Kết quả: 633 total, 447 unique, 186 duplicates (29.4%)
# → "User's name is Thảo My" xuất hiện 124 lần
```

## 1.2 Problem Statement — Phát biểu vấn đề

> ⚠️ **Luật:** Viết SYMPTOM trước. Chưa viết ROOT CAUSE ở bước này.
> Tách rõ: Mô tả (What) ≠ Nguyên nhân (Why) ≠ Giải pháp (How).

**Problem Statement (1-3 câu):**

```
Hệ thống mem0 đang lưu trùng lặp ~30% memories do logic deduplicate không hiệu quả.
Điều này gây ra:
- Tăng storage (124 lần memory "User's name is Thảo My" thay vì 1 lần)
- Giảm chất lượng search (semantic search trả về nhiều kết quả trùng)
- Tăng chi phí vector DB queries
- Ảnh hưởng trải nghiệm người dùng khi hiển thị memories
```

**Impact nhanh:**

| Category | Details |
|----------|---------|
| Users affected | ~50 users (từ sample export) |
| Features affected | Memory storage, Search, UI Display |
| Revenue / SLA | Tăng storage cost ~30%, degraded UX |

## 1.3 Context & Constraints — Bối cảnh và ràng buộc

> _Hiểu bối cảnh trước khi nhảy vào fix._

- **Hệ thống liên quan:** mem0 (vector store), Qdrant/Pgvector, LLM (fact extraction + update)
- **Thay đổi gần đây:** Production deployment Jan 2026
- **Ràng buộc:** Không được downtime, cần backward compatible
- **Đã có ai fix trước chưa?:** Chưa - đây là lần đầu phát hiện

---

# ═══════════════════════════════════════════════
# PHASE 2: NGUYÊN NHÂN — Tại sao xảy ra?
# ═══════════════════════════════════════════════

> _"Nghi ngờ suy nghĩ của chính mình. Trong mọi cuộc tìm giải pháp,"
> _đầu tiên hãy luôn nghĩ giải pháp của mình SAI."_
> _— First Principles: Bóc tách từng lớp, không chấp nhận bề mặt._

## 2.1 Hypothesis Generation — Đặt giả thuyết

> Liệt kê TẤT CẢ nguyên nhân có thể. Chưa cần đúng, cần ĐỦ.
> Dùng MECE: các giả thuyết không chồng chéo, bao phủ hết khả năng.

| # | Giả thuyết | Khả năng (%) | Cách kiểm chứng | Status |
|---|-----------|--------------|------------------|--------|
| H1 | Search chỉ limit=5, không tìm đủ memories cũ | High | Xem code `mem0/memory/main.py:479` | ✅ XÁC NHẬN |
| H2 | Search có filter run_id → không tìm xuyên suốt các session | High | Phân tích 276 run_id khác nhau | ✅ XÁC NHẬN |
| H3 | Hash được lưu nhưng không dùng để deduplicate | High | Xem code hash usage | ✅ XÁC NHẬN |
| H4 | LLM extract trùng fact từ messages | Medium | Check log LLM | ❌ LOẠI |
| H5 | Vector embedding similarity quá thấp không match | Low | Check vector store | ❌ LOẠI |

## 2.2 Investigation Log — Kiểm chứng từng giả thuyết

> Format: `[HH:MM] Giả thuyết → Hành động → Kết quả → Kết luận`
> Viết LIVE. Không cần đẹp. Cần ĐÚNG và ĐỦ.

```
[17:40] ── Test H1: Search limit=5 ──
         Action: Đọc code mem0/memory/main.py:479
         Result: existing_memories = self.vector_store.search(..., limit=5, ...)
         → ✅ XÁC NHẬN - limit=5 quá nhỏ cho user có hàng trăm memories

[17:45] ── Test H2: Search filter run_id ──
         Action: Phân tích tất cả run_id trong data export
         Result: 276 run_id unique cho 1 user! Mỗi conversation tạo run_id mới
         → ✅ XÁC NHẬN - Search với run_id mới không thấy memory từ run_id cũ

[17:50] ── Test H3: Hash not used for dedup ──
         Action: Kiểm tra code sử dụng hash trong search/dedup logic
         Result: Hash được lưu tại main.py:1138 nhưng KHÔNG được dùng trong search
         → ✅ XÁC NHẬN - Hash lưu nhưng không dùng để dedup

[17:55] ── Test H4: LLM extract duplicate facts ──
         Action: Check xem LLM có trả về ADD cho fact đã tồn tại không
         Result: Nhiều memory cùng hash "e17625f62118a3c7a3ccc3a7de1a0954" (User's name is Thảo My)
         → ❌ LOẠI - LLM không phải vấn đề, vấn đề là search không tìm thấy

[18:00] 💡 Insight: Cùng 1 fact "User's name is Thảo My" có 124 bản ghi với
         cùng hash nhưng KHÔNG run_id (79) và KHÁC run_id (554)
         → Search limit=5 + run_id filter = không bao giờ tìm thấy!
```

**Debug commands đã dùng (lưu lại để sau dùng):**

```bash
# Đếm duplicates trong memory export
python3 -c "
import json
from collections import Counter
with open('019b1b30-6579-74ba-ace2-51e39d116cdf.json') as f:
    data = json.load(f)
mem_counts = Counter([m['memory'] for m in data])
print(f'Total: {len(data)}, Unique: {len(mem_counts)}, Duplicates: {len(data)-len(mem_counts)}')
for mem, count in mem_counts.most_common(10):
    print(f'{count}x: {mem[:80]}...' if len(mem) > 80 else f'{count}x: {mem}')
"

# Xem chi tiết memory trùng
python3 -c "
import json
with open('019b1b30-6579-74ba-ace2-51e39d116cdf.json') as f:
    data = json.load(f)
thao_my = [m for m in data if m['memory'] == \"User's name is Thảo My\"][:3]
for m in thao_my:
    print(f'ID: {m[\"id\"]}, run_id: {m[\"run_id\"]}, hash: {m[\"hash\"]}, created: {m[\"created_at\"]}')
"
```

## 2.3 Root Cause — 5 Whys

> Hỏi "Tại sao?" cho đến khi tìm được điều CÓ THỂ FIX.

```
Symptom: Memory "User's name is Thảo My" bị lưu 124 lần

Why 1: Tại sao cùng 1 fact được lưu nhiều lần?
  → Vì mỗi lần user chat, hệ thống lại ADD memory mới

Why 2: Tại sao hệ thống không phát hiện fact đã tồn tại?
  → Vì search chỉ lấy 5 results gần nhất (limit=5)

Why 3: Tại sao limit=5 không đủ?
  → Vì user có 633 memories, chỉ search 5 → không tìm thấy fact cũ

Why 4: Tại sao có 633 memories?
  → Vì mỗi session tạo run_id mới (276 run_id), search theo run_id không hiệu quả

Why 5: Tại sao run_id filter gây vấn đề?
  → Vì search dùng filter {user_id, agent_id, run_id} thay vì chỉ user_id

✅ ROOT CAUSE: Search trong `_add_to_vector_store` dùng limit=5 + run_id filter
   → Không tìm thấy memories cũ → LLM ra lệnh ADD → Tạo memory trùng
```

**Contributing Factors (làm vấn đề tệ hơn / khó phát hiện hơn):**

| Factor | Ảnh hưởng | Preventable? |
|--------|-----------|--------------|
| Hash được lưu nhưng không dùng | Không có fallback dedup | ✅ |
| Không có monitoring duplicate rate | Không phát hiện sớm | ✅ |
| Test case không cover duplicate scenario | Không catch trước deploy | ✅ |

---

# ═══════════════════════════════════════════════
# PHASE 3: GIẢI PHÁP — Các hướng xử lý (MECE)
# ═══════════════════════════════════════════════

> _"Không chỉ fix — mà phải tạo đòn bẩy mới từ chính vấn đề."_
> _Liệt kê TẤT CẢ options → Đánh giá → Chọn → Giải thích tại sao loại các cái khác._

## 3.1 Solution Space — Các phương án

| # | Option | Mô tả (1-2 câu) | Effort | Risk | Leverage | Trade-off |
|---|--------|------------------|--------|------|----------|-----------|
| A | Tăng limit=5 → limit=50+ | Search nhiều hơn để LLM thấy memory cũ | 🟢 Low | 🟢 Low | 🟢 Medium | Có thể chậm hơn |
| B | Bỏ run_id filter trong search | Tìm xuyên suốt all sessions | 🟢 Low | 🟡 Medium | 🟢 Medium | Có thể match sai context |
| C | Thêm hash-based dedup | Kiểm tra hash trước khi lưu | 🟡 Medium | 🟢 Low | 🟡 High | Cần thêm DB query |
| D | Fix A + B + C | Kết hợp cả 3 | 🟡 Medium | 🟢 Low | 🔴 High | Tốt nhất |

> **Tiêu chí đánh giá:**
> - 🎯 Impact: Giải quyết triệt để vấn đề không?
> - ⏳ Urgency: Cần fix ngay hay có thể chờ?
> - 💪 Effort: Nguồn lực, thời gian cần bỏ ra?
> - 🔁 Leverage: Làm 1 lần dùng N lần? Có reuse được không?
> - ⚠️ Risk: Tệ nhất xảy ra là gì? Rollback được không?

## 3.2 Decision — Chọn phương án

> **Chọn: Option D**

| Item | Detail |
|------|--------|
| **Chọn** | Option D: Fix A + B + C |
| **Lý do chọn** | Giải quyết triệt để root cause: (1) tăng limit để search đủ, (2) bỏ run_id filter để tìm xuyên suốt, (3) thêm hash dedup làm fallback cuối cùng |
| **Rejected** | Option A/B: Chỉ fix 1 trong 3 nguyên nhân không đủ triệt để |
| **Rollback plan** | Revert code changes trong 5 phút |

---

# ═══════════════════════════════════════════════
# PHASE 4: THỬ NGHIỆM — Validate trước khi ship
# ═══════════════════════════════════════════════

> _Mỗi thử nghiệm = 1 giả thuyết + 1 test + 1 kết luận._
> _Fail nhanh, fail nhỏ, fail nhiều → tìm ra đáp án đúng._

## Experiment 1: Tăng limit từ 5 lên 50

| Item | Detail |
|------|--------|
| **Giả thuyết** | Nếu tăng limit=5 → limit=50 thì LLM sẽ thấy đủ memories cũ và ra lệnh NONE thay vì ADD |
| **Setup** | Thay đổi `limit=5` thành `limit=50` trong `mem0/memory/main.py:479` |
| **Expected** | Test case user có 633 memories, search trả về 50 results → LLM thấy fact trùng |
| **Actual** | [Chưa test] |
| **Kết luận** | ⏳ Chờ implement |

```bash
# Test command
```

---

## Experiment 2: Bỏ run_id filter trong search

| Item | Detail |
|------|--------|
| **Giả thuyết** | Nếu bỏ run_id filter thì search sẽ tìm xuyên suốt tất cả sessions |
| **Setup** | Sửa filter logic trong `mem0/memory/main.py:466-472` |
| **Expected** | Search chỉ filter theo user_id |
| **Actual** | [Chưa test] |
| **Kết luận** | ⏳ Chờ implement |

---

# ═══════════════════════════════════════════════
# PHASE 5: TRIỂN KHAI — Implementation
# ═══════════════════════════════════════════════

## 5.1 Changes — Các thay đổi

**Files changed:**

| File | Change | Why |
|------|--------|-----|
| `mem0/memory/main.py` | Tăng limit=5 → limit=50+ | Để search đủ memories cũ |
| `mem0/memory/main.py` | Bỏ run_id filter | Tìm xuyên suốt all sessions |
| `mem0/memory/main.py` | Thêm hash-based dedup | Fallback cuối cùng |

**Key code diff:**

```python
# ❌ BEFORE (main.py:466-481):
search_filters = {}
if filters.get("user_id"):
    search_filters["user_id"] = filters["user_id"]
if filters.get("agent_id"):
    search_filters["agent_id"] = filters["agent_id"]
if filters.get("run_id"):
    search_filters["run_id"] = filters["run_id"]
for new_mem in new_retrieved_facts:
    existing_memories = self.vector_store.search(
        query=new_mem,
        vectors=messages_embeddings,
        limit=5,  # QUÁ NHỎ!
        filters=search_filters,
    )

# ✅ AFTER:
# Chỉ search theo user_id (bỏ run_id để tìm xuyên suốt)
search_filters = {}
if filters.get("user_id"):
    search_filters["user_id"] = filters["user_id"]
# Agent_id có thể giữ nếu cần, nhưng run_id thì bỏ

for new_mem in new_retrieved_facts:
    existing_memories = self.vector_store.search(
        query=new_mem,
        vectors=messages_embeddings,
        limit=50,  # TĂNG LÊN
        filters=search_filters,
    )

# Thêm hash check trước khi create memory:
if new_mem_hash in existing_hashes:
    continue  # Skip - đã tồn tại
```

## 5.2 Deploy steps

```bash
# Step 1: Backup current code
git checkout main.py

# Step 2: Apply fix
# (edit code)

# Step 3: Test local
pytest tests/test_memory_dedup.py

# Step 4: Deploy to staging
git commit -m "fix: increase search limit + remove run_id filter + add hash dedup"
git push origin staging

# Step 5: Deploy to production
git push origin main
```

---

# ═══════════════════════════════════════════════
# PHASE 6: KIỂM TRA — Verify fix đã work
# ═══════════════════════════════════════════════

> ⚠️ Chạy TOÀN BỘ checklist **trước khi** đóng ticket.

## 6.1 Verification commands

```bash
# 1. Export một user có nhiều memories
python3 export_mem0_users.py --user_id TEST_USER_ID

# 2. Đếm duplicates
python3 -c "
import json
from collections import Counter
with open('TEST_USER_ID.json') as f:
    data = json.load(f)
mem_counts = Counter([m['memory'] for m in data])
print(f'Total: {len(data)}, Unique: {len(mem_counts)}, Duplicates: {len(data)-len(mem_counts)}')
dupe_rate = (len(data)-len(mem_counts))/len(data)*100
print(f'Duplicate rate: {dupe_rate:.1f}%')
# Expected: < 1%
"
```

## 6.2 Verification checklist

- [ ] Symptom ban đầu đã hết (test lại reproduce steps)
- [ ] Duplicate rate < 1%
- [ ] Memory "User's name is Thảo My" chỉ xuất hiện 1 lần
- [ ] Không có side effect mới (search vẫn hoạt động)
- [ ] Rollback plan đã test (nếu cần)

## 6.3 Metrics Before vs After

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Duplicate rate | 29.4% | TBD | < 1% |
| "Thảo My" memory count | 124 | TBD | 1 |
| Search latency | TBD | TBD | < 500ms |

---

# ═══════════════════════════════════════════════
# PHASE 7: ĐÚC KẾT — Kaizen & Knowledge Capture
# ═══════════════════════════════════════════════

> _"Không đo lường — Không cải tiến."_
> _Viết phần này SAU KHI resolve. Đúc kết từ Phase 1-6 thành knowledge tái sử dụng._

---

## 7.1 Common Mistakes — Các lỗi đã mắc

> Format: ❌ Sai (tại sao sai) → ✅ Đúng (tại sao đúng) → 🔍 Detect (cách tìm trong code)

### M-01: Search limit quá nhỏ cho large dataset

**Severity:** 🟠 SEV-2

❌ **Sai — Đừng làm thế này:**
```python
existing_memories = self.vector_store.search(
    query=new_mem,
    vectors=messages_embeddings,
    limit=5,  # QUÁ NHỎ cho user có 100+ memories
    filters=search_filters,
)
```
> **Tại sao sai:** Khi user có hàng trăm memories, search chỉ 5 results gần nhất không đủ để LLM so sánh. LLM không thấy fact cũ → ra lệnh ADD → tạo duplicate.

**Dấu hiệu nhận biết:**
```
Duplicate rate > 10%
Cùng 1 fact xuất hiện > 10 lần trong export
```

✅ **Đúng — Làm thế này:**
```python
existing_memories = self.vector_store.search(
    query=new_mem,
    vectors=messages_embeddings,
    limit=50,  # ĐỦ LỚN để cover hầu hết cases
    filters=search_filters,
)
```
> **Tại sao đúng:** Với limit=50, khả năng LLM thấy fact cũ cao hơn đáng kể.

🔍 **Detect trong codebase:**
```bash
grep -rn "limit=5" mem0/ --include="*.py"
```

---

### M-02: Search filter quá hẹp (run_id) không tìm xuyên suốt

**Severity:** 🟠 SEV-2

❌ **Sai:**
```python
search_filters = {}
if filters.get("user_id"):
    search_filters["user_id"] = filters["user_id"]
if filters.get("run_id"):  # ĐÂY LÀ VẤN ĐỀ
    search_filters["run_id"] = filters["run_id"]
```
> **Tại sao sai:** Mỗi conversation tạo run_id mới. Search với run_id mới không tìm thấy memory từ session cũ.

✅ **Đúng:**
```python
search_filters = {}
if filters.get("user_id"):
    search_filters["user_id"] = filters["user_id"]
# Bỏ run_id filter - tìm xuyên suốt all sessions
```

🔍 **Detect trong codebase:**
```bash
grep -rn "run_id" mem0/memory/main.py | grep -i filter
```

---

### M-03: Hash được lưu nhưng không dùng để deduplicate

**Severity:** 🟡 SEV-3

❌ **Sai:**
```python
# Lưu hash
metadata["hash"] = hashlib.md5(data.encode()).hexdigest()
# Nhưng KHÔNG dùng để check trùng
```
> **Tại sao sai:** Hash là một cách dedup hiệu quả, nhưng không được sử dụng.

✅ **Đúng:**
```python
# Lưu hash
metadata["hash"] = hashlib.md5(data.encode()).hexdigest()

# Dùng hash để dedup
existing_hashes = [m.payload.get("hash") for m in existing_memories]
if hash in existing_hashes:
    continue  # Skip - đã tồn tại
```

---

## 7.2 Best Practices Checklist — Rút ra từ vấn đề này

> ✅ Must-have — Bắt buộc | ⚠️ Should-have — Nên có | 💡 Nice-to-have

### [Category 1 — Data Deduplication]

- [ ] ✅ Search limit phải đủ lớn (≥50) cho dataset có 100+ records
- [ ] ✅ Không filter quá hẹp khi search để dedup (bỏ run_id)
- [ ] ✅ Dùng hash làm fallback dedup cuối cùng
- [ ] ⚠️ Thêm monitoring duplicate rate vào dashboard

### [Category 2 — Testing]

- [ ] ✅ Test case cover duplicate scenario (user có >100 memories)
- [ ] ⚠️ Test với nhiều sessions (nhiều run_id)

### Verification commands cho checklist:
```bash
# Check limit trong code
grep -rn "limit=" mem0/memory/main.py

# Check run_id filter
grep -rn "run_id" mem0/memory/main.py | grep filter
```

---

## 7.3 Action Items — Ngăn tái phát

| # | Action | Priority | Owner | Due | Status | Ticket |
|---|--------|----------|-------|-----|--------|--------|
| 1 | Fix limit=5 → 50+ trong search | P1 | @cuong | 2026-03-17 | ⏳ | #xxx |
| 2 | Bỏ run_id filter trong dedup search | P1 | @cuong | 2026-03-17 | ⏳ | #xxx |
| 3 | Thêm hash-based dedup fallback | P2 | @cuong | 2026-03-18 | ⏳ | #xxx |
| 4 | Thêm monitoring duplicate rate | P2 | @cuong | 2026-03-20 | ⏳ | #xxx |
| 5 | Viết test case duplicate scenario | P3 | @cuong | 2026-03-22 | ⏳ | #xxx |

**Detection improvements (phát hiện sớm hơn lần sau):**

- [ ] Alert: `duplicate_rate > 5%` for `duration: 5m`
- [ ] Dashboard: Panel "Memory Duplicate Rate" by user
- [ ] Log: Thêm log khi LLM ra ADD command cho fact trùng
- [ ] Test: Scenario với user có 500+ memories

---

## 7.4 Lessons Learned

**Làm tốt ✅ (lặp lại):**
- Phân tích data export để phát hiện vấn đề
- Dùng Counter để đếm duplicates chính xác
- Trace root cause qua 5 Whys

**Cần cải thiện ⚠️ (fix process):**
- Cần có monitoring duplicate rate từ đầu
- Test case cần cover large dataset scenarios

**Câu hỏi mở ❓ (research thêm):**
- Liệu có cần dedup ở layer khác không (vector store level)?
- Nếu user có 10,000 memories thì sao? limit=50 có đủ không?

---

## 7.5 Quick Reference Card

> Copy-paste vào onboarding doc / team wiki.

```
╔══════════════════════════════════════════════════════════╗
║  MEM0 — Quick Ref from PROB-2026-03-17-memory-duplicate║
╠══════════════════════════════════════════════════════════╣
║  🔴 M-01: Search limit=5 → đặt ≥50 cho large dataset   ║
║  🔴 M-02: Run_id filter → bỏ khi dedup search          ║
║  🟠 M-03: Hash stored but unused → dùng hash dedup    ║
╠══════════════════════════════════════════════════════════╣
║  ✅ BP-01: Monitor duplicate rate per user              ║
║  ✅ BP-02: Test với 100+ memories trước deploy         ║
╠══════════════════════════════════════════════════════════╣
║  Debug: grep -rn "limit=" mem0/memory/main.py           ║
║  Doc: [link tới file này]                               ║
╚══════════════════════════════════════════════════════════╝
```

---

# APPENDIX

## A. Relevant logs

```
[Export data analysis]
User: 019b1b30-6579-74ba-ace2-51e39d116cdf
Total memories: 633
Unique: 447
Duplicates: 186 (29.4%)

Top duplicates:
- "User's name is Thảo My": 124 lần (hash: e17625f62118a3c7a3ccc3a7de1a0954)
- "User's name is Thảo Mi": 24 lần
- "User is happy this week": 6 lần
```

## B. System diagram / Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Conversation                            │
│  run_id = "session_123"  →  run_id = "session_456"            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              mem0.add(messages, user_id, run_id)                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Extract facts via LLM                                   │
│  → "User's name is Thảo My"                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: Search existing memories                               │
│  ❌ PROBLEM: limit=5 + run_id filter                            │
│  → Không tìm thấy fact cũ (vì 5 results không đủ)              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: LLM decides                                            │
│  ❌ PROBLEM: Không thấy duplicate → ADD command                 │
│  → Tạo memory mới thay vì NONE                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Result: Same fact stored 124 times!                            │
└─────────────────────────────────────────────────────────────────┘
```

## C. References

- [mem0/memory/main.py:479](mem0/memory/main.py#L479) - Search limit
- [mem0/memory/main.py:466-472](mem0/memory/main.py#L466) - Search filters
- [scripts/mem0_export_50_users_20260316_160255/](scripts/mem0_export_50_users_20260316_160255/) - Export data

---

# REPORT FORMAT (Dùng khi báo cáo cho stakeholder)

> Copy section này khi cần gửi report ngắn gọn cho manager / team khác.

```
1. VẤN ĐỀ:    Hệ thống mem0 lưu trùng lặp 29.4% memories
   IMPACT:     124 lần memory "User's name is Thảo My", tăng storage 30%
   METRICS:    633 total → 447 unique (186 duplicates)

2. NGUYÊN NHÂN: Search limit=5 + run_id filter → không tìm thấy fact cũ
   DẪN CHỨNG:   276 run_id khác nhau, search chỉ 5 results gần nhất

3. GIẢI PHÁP:  Tăng limit=50, bỏ run_id filter, thêm hash dedup
   DẪN CHỨNG:   [Chờ implement]

4. PREVENT:    Monitor duplicate rate, test large dataset, dùng hash dedup
```

---

*Created by `@cuong` on `2026-03-17` · Last updated: `2026-03-17`*
*Naming: `PROB-YYYY-MM-DD-[slug].md` — VD: `PROB-2026-03-17-memory-duplicate.md`*
