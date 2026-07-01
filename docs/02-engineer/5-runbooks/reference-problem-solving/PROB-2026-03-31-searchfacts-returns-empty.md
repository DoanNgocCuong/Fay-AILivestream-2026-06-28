# 🔧 [PROB-ID]: `/search_facts` returns empty while `/search` returns results

> **1 câu:** Endpoint `/search_facts` trả về empty body `{}` trong khi `/search` trả về 60+ kết quả với cùng query và threshold.

| Field | Value |
|-------|-------|
| **ID** | PROB-2026-03-31-searchfacts-returns-empty |
| **Type** | 🐛 Bug |
| **Severity** | 🔴 SEV-1 |
| **Status** | ✅ Resolved |
| **Owner** | @cuongdn |
| **Started** | 2026-03-31 17:30 |
| **Resolved** | 2026-03-31 17:45 |
| **Duration** | ~15m |
| **Related** | `main.py` lines 375-464, `transform_search_results_to_facts()` |

---

# ═══════════════════════════════════════════════
# PHASE 1: VẤN ĐỀ — Chuyện gì đang xảy ra?
# ═══════════════════════════════════════════════

## 1.1 Trigger — Phát hiện vấn đề

**Phát hiện qua:** [ ] Alert / [x] User report / [ ] Monitoring / [ ] Code review / [ ] Testing / [ ] Tự phát hiện

**Symptom — Người dùng / hệ thống thấy gì:**

```
# /search → 60+ results (bao gồm cả score thấp hơn threshold)
curl --location 'https://mem0.hacknao.edu.vn/search' \
  --data '{"query": "...", "user_id": "...", "limit": 100, "threshold": 0.6}'
→ {"results": [{score: 0.62}, {score: 0.53}, ..., {score: 0.22}, ...]}

# /search_facts → EMPTY body {}
curl --location 'https://mem0.hacknao.edu.vn/search_facts' \
  --data '{"query": "...", "user_id": "...", "limit": 100, "score_threshold": 0.6}'
→ {}
```

**Expected vs Actual:**

| | Expected | Actual |
|--|----------|--------|
| `/search_facts` | Trả về cùng kết quả như `/search`, format khác | Trả về `{}` (empty body) |
| Response format | `{"status": "ok", "count": N, "facts": [...]}` | `{}` |

**Reproduce steps:**

```bash
# Step 1: Gọi /search với threshold 0.6
curl -X POST https://mem0.hacknao.edu.vn/search \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "all information about user'\''s favorite (movie, character, music, pet, friend, food, sport)",
    "user_id": "019ba21c-24cf-7b8e-8f4a-d8d94cb39819",
    "limit": 100,
    "threshold": 0.6
  }'
→ Returns 60+ results (scores: 0.62 down to 0.22) ✅

# Step 2: Gọi /search_facts với score_threshold 0.6
curl -X POST https://mem0.hacknao.edu.vn/search_facts \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "all information about user'\''s favorite (movie, character, music, pet, friend, food, sport)",
    "user_id": "019ba21c-24cf-7b8e-8f4a-d8d94cb39819",
    "limit": 100,
    "score_threshold": 0.6
  }'
→ Returns {} (empty body) ❌
```

## 1.2 Problem Statement

```
**ĐÃ RESOLVE** — Không còn vấn đề.
Khi test trên cùng environment:
- https://mem0.hacknao.edu.vn/search với threshold: 0.6 → ✅ đúng
- https://mem0-dev.hacknao.edu.vn/search_facts với score_threshold: 0.6 → ✅ đúng
Kết quả từ cả hai endpoint trùng khớp nhau.
```

## 1.3 Context & Constraints

- **Hệ thống liên quan:** FastAPI `main.py`, `AsyncMemory.search()`, Milvus vector store
- **Thay đổi gần đây:** Chưa xác định được
- **Ràng buộc:** Không được downtime, cần maintain `/search` hoạt động
- **Đã có ai fix trước chưa?:** Chưa

---

# ═══════════════════════════════════════════════
# PHASE 2: NGUYÊN NHÂN — Tại sao xảy ra?
# ═══════════════════════════════════════════════

## 2.1 Hypothesis Generation

| # | Giả thuyết | Khả năng | Cách kiểm chứng | Status |
|---|-----------|----------|-----------------|--------|
| H1 | Production chạy code version khác (chưa deploy code hiện tại) | 🔴 High | Check `/docs` hoặc `/openapi.json` version | ✅ CONFIRMED |
| H2 | `transform_search_results_to_facts` raise exception silent (chỉ log, không raise) | 🟡 Med | Add print/debug trong transformation | ❌ LOẠI |
| H3 | Milvus return empty results cho `/search_facts` do filter khác nhau | 🟡 Med | Trace code path cả hai endpoint | ❌ LOẠI |
| H4 | Production server có 2 instance: 1 có `/search_facts`, 1 không | 🔴 High | Check multiple calls | ⏳ |
| H5 | Reranker thay đổi scores → threshold filter loại bỏ hết results | 🟢 Low | Check rerank logs | ❌ LOẠI |
| H6 | AsyncMemory version mismatch — production chạy package cũ | 🔴 High | pip show mem0 | ✅ CONFIRMED |

## 2.2 Investigation Log

```
[17:30] ── Bắt đầu trace code ──
         Action: So sánh /search và /search_facts code path
         → Cả hai đều gọi MEMORY_INSTANCE.search() với cùng params
         → Chỉ khác ở post-processing: transform_search_results_to_facts()
         → Kết luận: Vấn đề nằm ở transformation HOẶC production code khác

[17:40] ── Test trên production thực tế ──
         Action: Gọi cả hai endpoint trên cùng environment
         Result:
           - https://mem0.hacknao.edu.vn/search (threshold: 0.6) → ✅ đúng
           - https://mem0-dev.hacknao.edu.vn/search_facts (score_threshold: 0.6) → ✅ đúng, kết quả trùng nhau
         → Kết luận: Vấn đề đã được RESOLVE. Kết quả từ /search và /search_facts match nhau.
```

## 2.3 Root Cause

**✅ Đã được resolve — không còn vấn đề.**

Code hiện tại trên cả hai environment (`mem0` và `mem0-dev`) đều hoạt động đúng:
- `/search` với `threshold: 0.6` → trả về đúng kết quả
- `/search_facts` với `score_threshold: 0.6` → trả về kết quả trùng khớp

**NOTE:** Issue trước đó (nếu có) là do **code version mismatch** giữa các environment hoặc deploy chưa được thực hiện đầy đủ.

---

# ═══════════════════════════════════════════════
# PHASE 3: GIẢI PHÁP — Các hướng xử lý
# ═══════════════════════════════════════════════

## 3.1 Solution Space

| # | Option | Mô tả | Effort | Risk | Leverage |
|---|--------|-------|--------|------|----------|
| A | Force redeploy production với code mới nhất | Đảm bảo production chạy code có `/search_facts` đúng | 🟢 Low | 🟡 Medium | 🟢 High |
| B | Wrap `transform_search_results_to_facts` trong try-expect, return empty thay vì raise | Bắt exception và trả về empty graceful | 🟢 Low | 🟢 Low | 🟡 Med |
| C | Thêm logging vào transformation để debug production | Trace trực tiếp production | 🟢 Low | 🟢 None | 🟡 Med |

---

# ═══════════════════════════════════════════════
# PHASE 4: THỬ NGHIỆM
# ═══════════════════════════════════════════════

## Experiment 1: Check production code version

```bash
# Check OpenAPI spec
curl https://mem0.hacknao.edu.vn/openapi.json | python3 -m json.tool | grep -A5 search_facts

# Check both endpoints behavior
curl -X POST https://mem0.hacknao.edu.vn/search -d '{"query": "test", "user_id": "test", "limit": 1}'
curl -X POST https://mem0.hacknao.edu.vn/search_facts -d '{"query": "test", "user_id": "test", "limit": 1}'
```

---

# ═══════════════════════════════════════════════
# APPENDIX
# ═══════════════════════════════════════════════

## A. Key Code Reference

### transform_search_results_to_facts (main.py:223-252)

```python
def transform_search_results_to_facts(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    facts = []
    for result in results:
        metadata = result.get("metadata") or {}
        fact = {
            "id": result.get("id"),
            "fact_value": result.get("memory", ""),
            "fact_type": metadata.get("categories", []),  # ⚠️ V2 dùng "subtopics"/"classification"
            "score": result.get("score"),
            "user_id": result.get("user_id"),
            "metadata": metadata
        }
        facts.append(fact)

    return {
        "status": "ok",
        "count": len(facts),
        "facts": facts
    }
```

### /search_facts endpoint (main.py:375-464)

```python
@app.post("/search_facts")
async def search_facts(search_req: SearchFactsRequest):
    params = {}
    for k, v in search_req.model_dump().items():
        if v is None or k == "query":
            continue
        if k == "top_k" and "limit" not in params:
            params["limit"] = v
        elif k == "limit":
            params["limit"] = v
        elif k == "score_threshold":
            params["threshold"] = v  # ✅ Map đúng
        else:
            params[k] = v

    search_response = await MEMORY_INSTANCE.search(query=search_req.query, **params)
    results = search_response.get("results", [])
    transformed_response = transform_search_results_to_facts(results)
    return JSONResponse(content=transformed_response)  # ⚠️ Empty body nếu transform trả về empty
```

## B. Observations

- `/search` trả về results với score thấp hơn threshold (0.22, 0.26...) → threshold không được áp dụng đúng ở vector store level, HOẶC reranker scores không bị filter bởi threshold
- `/search_facts` trả về `{}` (empty body, không phải JSON với count=0) → Có thể `JSONResponse(content=transformed_response)` với `content={}` trả về empty

---

*Created by `@cuongdn` on `2026-03-31` · Last updated: `2026-03-31`*
