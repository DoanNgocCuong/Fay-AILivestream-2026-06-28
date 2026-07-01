# Knowledge Base — Dr.Bee Nhộng Ong Haircare

## Tổng quan

File: `fay_player_knowledge/drbee-nhuong-ong-haircare.zip`  
Format: Fay Player course zip (có `manifest.json`)  
MCP Server: `课程知识库` (autostart: true)

Knowledge base này thay thế file demo `OfficeEcho-course.zip` (đã xóa).  
AI sẽ dùng dữ liệu này để tư vấn sản phẩm Nhộng Ong Haircare của Dr.Bee.

---

## Cấu trúc file zip

```
drbee-nhuong-ong-haircare.zip
├── manifest.json              ← BẮT BUỘC — metadata + danh sách sections
└── sections/
    ├── 01-s01/
    │   └── script.txt         ← Nội dung text của section 1
    ├── 02-s02/
    │   └── script.txt
    ├── 03-s03/
    │   └── script.txt
    ├── 04-s04/
    │   └── script.txt
    ├── 05-s05/
    │   └── script.txt
    └── 06-s06/
        └── script.txt
```

### manifest.json (format đầy đủ)

```json
{
  "id": "drbee-nhuong-ong-haircare",
  "title": "Dr.Bee — Nhộng Ong Haircare",
  "author": "Dr.Bee",
  "version": "1.0.0",
  "color": "#f5a623",
  "icon": "🐝",
  "description": "Kiến thức sản phẩm Nhộng Ong Haircare — dành cho AI tư vấn bán hàng",
  "sections": [
    {
      "id": "s01",
      "title": "Nhộng Ong Haircare là gì?",
      "script": "sections/01-s01/script.txt",
      "assets": [],
      "quiz": ""
    },
    {
      "id": "s02",
      "title": "So sánh với dầu gội thông thường",
      "script": "sections/02-s02/script.txt",
      "assets": [],
      "quiz": ""
    }
  ]
}
```

**Các field bắt buộc của manifest:**
- `id` — ID duy nhất của course (dùng để tạo `source_id`)
- `title` — Tên hiển thị
- `sections` — Mảng danh sách sections (ít nhất 1 section)

**Các field bắt buộc của mỗi section:**
- `id` — ID của section (vd: `s01`)
- `title` — Tên section
- `script` — Đường dẫn đến file `.txt` chứa nội dung (relative trong zip)

**Các field tùy chọn:**
- `author`, `version`, `description`, `color`, `icon` — metadata hiển thị
- `assets` — Danh sách ảnh/code đính kèm (có thể để `[]`)
- `quiz` — Câu hỏi quiz (có thể để `""`)

---

## Cách đóng gói zip từ đầu

### Bước 1 — Chuẩn bị nội dung

Tạo folder tạm với cấu trúc:
```
my_kb/
├── manifest.json
└── sections/
    ├── 01-s01/
    │   └── script.txt   ← nội dung text thuần
    └── 02-s02/
        └── script.txt
```

Mỗi `script.txt` là text thuần (UTF-8), không cần markdown đặc biệt. Ví dụ:

```
Nhộng Ong Haircare là dòng sản phẩm chăm sóc tóc cao cấp của Dr.Bee.

Sản phẩm đã được Bộ Y Tế cấp phép, an toàn tuyệt đối.
KHÔNG SLS, KHÔNG Paraben, KHÔNG Silicone.
```

### Bước 2 — Tạo manifest.json

Tạo file `manifest.json` theo format trên. Mỗi section cần có entry tương ứng trong `sections[]`.

### Bước 3 — Nén thành zip

**Cách 1 — Dùng Python (khuyến nghị, tránh lỗi encoding):**

```python
import zipfile, json

sections_data = [
    {
        'id': 's01',
        'title': 'Tiêu đề section 1',
        'script': 'Nội dung text của section 1...'
    },
    {
        'id': 's02',
        'title': 'Tiêu đề section 2',
        'script': 'Nội dung text của section 2...'
    },
]

manifest = {
    'id': 'my-knowledge-base',
    'title': 'Tên Knowledge Base',
    'author': 'Tác giả',
    'version': '1.0.0',
    'description': 'Mô tả ngắn',
    'sections': []
}

for i, s in enumerate(sections_data):
    idx = str(i + 1).zfill(2)
    manifest['sections'].append({
        'id': s['id'],
        'title': s['title'],
        'script': f"sections/{idx}-{s['id']}/script.txt",
        'assets': [],
        'quiz': ''
    })

with zipfile.ZipFile('my-knowledge-base.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    for i, s in enumerate(sections_data):
        idx = str(i + 1).zfill(2)
        folder = f"sections/{idx}-{s['id']}/"
        zf.writestr(folder, '')                          # tạo directory entry
        zf.writestr(f"{folder}script.txt", s['script']) # ghi nội dung

print('Done!')
```

**Cách 2 — Dùng Windows Explorer:**
1. Tạo folder `my_kb/` với đúng cấu trúc như trên
2. Chọn tất cả file bên trong → chuột phải → "Compress to ZIP file"
3. **Lưu ý**: phải nén từ BÊN TRONG folder (không nén cả folder), để `manifest.json` nằm ở root của zip

### Bước 4 — Đặt file zip vào thư mục

```
d:\GIT\Fay\fay_player_knowledge\my-knowledge-base.zip
```

MCP server sẽ tự detect và load trong vòng **60 giây**.

Hoặc force reload ngay bằng tool `kb_reload` với `source_id` tương ứng.

---

## Script build hiện tại (Dr.Bee)

File script build knowledge base Dr.Bee hiện tại: [`data/build_kb_drbee.py`](../../data/build_kb_drbee.py)

Chạy lại khi cần cập nhật nội dung:
```bash
python data/build_kb_drbee.py
```

---

## Sections hiện tại

| # | Section ID | Tiêu đề | Nội dung chính |
|---|-----------|---------|----------------|
| 1 | s01 | Nhộng Ong Haircare là gì? | Giới thiệu, cam kết Bộ Y Tế, link Fanpage |
| 2 | s02 | So sánh với dầu gội thông thường | Clear/Sunsilk vs Nhộng Ong, câu chốt sale |
| 3 | s03 | Tại sao KHÔNG SLS – Paraben – Silicone | Tác hại từng chất, an toàn cho da nhạy cảm |
| 4 | s04 | Thành phần chính & Hoạt chất | Nhộng Ong, Nhân Sâm, Collagen, Vitamin B |
| 5 | s05 | Combo & Giá bán | Giá lẻ 280k, Combo 599k, Combo 1.1tr, cam kết hoàn tiền |
| 6 | s06 | USP & Script tư vấn cho sale | Ý chính tư vấn, điểm bán hàng độc đáo, câu chốt |

---

## Cách MCP Server load

Cấu hình trong `faymcp/data/mcp_servers.json`:

```json
{
  "name": "课程知识库",
  "command": "python",
  "args": [
    "mcp_servers/fay_player_knowledge/fay_player_knowledge_base_mcp_server.py",
    "--source",
    "./fay_player_knowledge"
  ],
  "autostart": true
}
```

Server tự scan `fay_player_knowledge/` mỗi 60 giây. Bất kỳ `.zip` nào có `manifest.json` đều được index tự động.

---

## Tools MCP để quản lý

| Tool | Dùng khi nào |
|------|-------------|
| `kb_list_sources` | Kiểm tra file nào đang được load |
| `kb_get_catalog` | Xem mục lục sections của một source |
| `kb_search` | Tìm kiếm nội dung (AI tự gọi khi cần) |
| `kb_reload` | Force reload ngay sau khi cập nhật file zip |

---

## Lưu ý

- **Script build dùng ASCII** cho nội dung để tránh lỗi encoding trên Windows. AI vẫn hiểu đúng ngữ nghĩa.
- **Embedding API** hiện đang disabled (dùng mock vector) → search bằng keyword. Khi enable lại thì search quality tốt hơn nhiều.
- **Không cần restart** Fay khi thêm/sửa file zip — MCP server tự detect.
