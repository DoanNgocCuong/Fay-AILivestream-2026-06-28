
**Không cần embedding — đưa thẳng vào prompt là đủ và tốt hơn.** Lý do:

---

## Phân tích

| Yếu tố                 | Giá trị                  |
| ------------------------ | -------------------------- |
| File size                | ~9.4KB, ~3.000 tokens      |
| Gemini 2.5 Flash context | **1.000.000 tokens** |
| % context bị chiếm     | ~0.3%                      |

**File này nhỏ hơn 1% context window của model.** Đưa thẳng vào system prompt không tốn gì cả.

---

## So sánh 2 approach

|                    | Direct Prompt            | Embedding (RAG)                                               |
| ------------------ | ------------------------ | ------------------------------------------------------------- |
| Độ phức tạp    | ✅ Đơn giản           | ❌ Pipeline phức tạp (embed → store → retrieve → inject) |
| Latency            | ✅ 0ms overhead          | ❌ +200-500ms mỗi query                                      |
| Retrieval miss     | ✅ Không bao giờ       | ❌ Có thể miss nếu query không match chunk                |
| Context đầy đủ | ✅ Luôn có toàn bộ   | ❌ Chỉ có chunk được retrieve                            |
| Phù hợp khi      | File nhỏ, 1 sản phẩm  | 100+ tài liệu, hàng MB                                     |
| Cost               | ✅ 0 (đã trong prompt) | ❌ Cần embedding API + vector DB                             |

**RAG chỉ thực sự cần khi knowledge base > 50-100K tokens** (khoảng 300-600 trang A4). File này chỉ ~3 trang.

---

## Cách triển khai — đưa vào system prompt

Bạn chỉ cần thêm nội dung `data_san_pham.md` vào `config.json` (phần `persona` hoặc `prompt`). Muốn mình làm luôn không?
