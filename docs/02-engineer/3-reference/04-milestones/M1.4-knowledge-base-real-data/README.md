# M1.4 — Knowledge Base thực tế Dr.Bee

**Trạng thái:** ✅ Hoàn thành

## Mục tiêu

Nhét data sản phẩm thực tế vào để AI tư vấn chính xác — không bịa giá, không nhầm thành phần, không sai cam kết.

## Quyết định: Direct Inject vs RAG

| Tiêu chí | Direct Inject ✅ | RAG/Embedding |
|---|---|---|
| File size | ~3.000 tokens (0,3% context 1M) | Cần chunking |
| Retrieval miss | Không bao giờ | Có thể miss |
| Latency overhead | 0ms | +100–500ms |
| Setup | 5 dòng code | Embedding API + vector DB |
| Bug risk | Thấp | Cao |

**Kết luận:** File nhỏ → inject thẳng vào system prompt.

## Implementation

```python
# llm/nlp_cognitive_stream.py — inject sau MCP Resources block
_kb_path = os.path.join(project_root, "data", "data_san_pham.md")
with open(_kb_path, encoding="utf-8") as f:
    _kb_content = f.read().strip()

system_prompt += (
    "\n\n**KIẾN THỨC SẢN PHẨM DR.BEE**\n"
    "Dùng thông tin dưới đây để tư vấn chính xác. KHÔNG bịa thêm thông tin ngoài phạm vi này.\n\n"
    + _kb_content + "\n"
)
```

## Nội dung `data/data_san_pham.md`

| Mục | Chi tiết |
|---|---|
| Sản phẩm | Dầu gội Nhộng Ong Dr.Bee (trị gàu, nấm, rụng tóc) |
| Thành phần | Nhộng Ong, Nhân Sâm, Collagen, Vitamin B5/B7 |
| Không chứa | SLS, Paraben, Silicone |
| Giá | 280K/hộp · Combo 2 hộp 599K · Combo 4 hộp 1.100K |
| Cam kết | Hoàn tiền 100% sau 15 ngày |
| So sánh | vs Clear, Sunsilk, Pantene, Dove |

## Mở rộng tương lai

Nếu KB > 50.000 tokens → chuyển sang RAG:
- Embed chunks: `text-embedding-004`
- Vector store: ChromaDB local
- Retrieve top-3 chunks theo query viewer

## Files

| File | Vai trò |
|---|---|
| `data/data_san_pham.md` | Knowledge base sản phẩm |
| `llm/nlp_cognitive_stream.py` | Inject vào system prompt |
