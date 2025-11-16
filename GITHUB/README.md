# 🎬 FilmAI - Hệ Thống Tạo Prompt Phim Tự Động

Hệ thống tự động hóa hoàn chỉnh để tạo **Super JSON Prompts** cho AI Video (Runway, Pika, Sora, Kling...) với tính năng:

✅ **Character Lock** - Nhân vật nhất quán
✅ **Close-up Detection** - Tự động đổi tên khi cận cảnh
✅ **AI Auto Camera/Style** - Gemini 2.5 Flash tự chọn góc quay
✅ **Dual Language Output** - Tiếng Anh + Tiếng Việt riêng biệt
✅ **API Rotation** - 10 Gemini keys xoay vòng tự động

---

## 📂 Cấu Trúc File

```
GITHUB/
├── character_dictionary.json    # Định nghĩa nhân vật (appearance, voice_tone)
├── scenes.txt                   # Input: Danh sách 60 cảnh
├── scenes_test.txt              # File test nhỏ (4 cảnh)
├── api_keys.txt                 # 10 Gemini API keys (1 key/dòng)
├── generate_prompts.py          # Node 2: Sinh Super JSON
├── translate_prompts.py         # Node 3: Xuất EN/VI
├── output_prompts.txt           # Output từ Node 2
├── final_prompts_en.txt         # Output tiếng Anh
└── final_prompts_vi.txt         # Output tiếng Việt
```

---

## 🚀 Workflow

```
scenes.txt → Node 2 (generate_prompts.py) → output_prompts.txt
                                                    ↓
                          Node 3 (translate_prompts.py)
                                    ↓
                    final_prompts_en.txt + final_prompts_vi.txt
```

---

## 🎯 Cách Sử Dụng

### **Bước 1: Chuẩn bị Character Dictionary**

Chỉnh sửa `character_dictionary.json`:

```json
{
  "characters": [
    {
      "name": "Alex",
      "name_closeup": "Alex2",
      "appearance": "36-year-old athletic man with short brown hair...",
      "voice_tone": "Deep, commanding, confident"
    }
  ]
}
```

### **Bước 2: Tạo File Scenes**

Chỉnh sửa `scenes.txt` (hoặc dùng `scenes_test.txt` để test):

```
Scene 1: Alex stands on a rooftop overlooking the city...

Scene 2: Close-up of Maya's face as she reads...

Scene 3: Marcus enters the abandoned warehouse...
```

### **Bước 3: Chạy Node 2 - Sinh Super JSON**

```bash
cd GITHUB
python generate_prompts.py
```

**Output:** `output_prompts.txt` - Mỗi dòng là 1 JSON siêu cấu trúc

### **Bước 4: Chạy Node 3 - Xuất EN/VI**

```bash
python translate_prompts.py
```

**Output:**
- `final_prompts_en.txt` - Tiếng Anh
- `final_prompts_vi.txt` - Tiếng Việt

---

## 🔑 Tính Năng Chính

### **1. Character Lock (Nhân vật nhất quán)**

- Định nghĩa nhân vật 1 lần trong `character_dictionary.json`
- Tất cả cảnh tự động dùng đúng `appearance` và `voice_tone`
- Không cần ghi lại mô tả mỗi cảnh

### **2. Close-up Detection**

AI tự động phát hiện cảnh cận cảnh và đổi tên:

| Shot Type | Focus Characters |
|-----------|-----------------|
| Wide / Medium | `["Alex", "Maya"]` |
| Close-up / Extreme Close-up | `["Alex2", "Maya2"]` |

### **3. AI Auto Camera/Style**

Gemini 2.5 Flash tự động chọn:
- Camera angle & movement
- Shot type (wide/medium/close-up/extreme close-up)
- Lighting style
- Cinematic effects

### **4. Super JSON Structure**

Mỗi cảnh = 1 dòng JSON hoàn chỉnh:

```json
{"scene_number":1,"scene_title":"...","character":{"name":"Alex","appearance":"...","emotions":{"primary":"...","secondary":"..."},"voice_tone":"..."},"setting":{"location":"...","environment":"...","time":"..."},"cinematic":{"camera":"...","shot_type":"close-up","focus_characters":["Alex2"],"lighting":"...","mood":"...","style":"Cinematic 8K realistic","effects":"...","sound":"..."},"dialogue":{"characters":[{"speaker":"...","line":"..."}]},"action_block":{"length":"150-200 words","content":"..."}}
```

### **5. API Rotation**

- 10 Gemini API keys tự động xoay vòng
- Khi 1 key hết quota → tự động chuyển sang key khác
- Không bao giờ bị gián đoạn

---

## 📦 Yêu Cầu Hệ Thống

```bash
pip install google-generativeai
```

**Python:** 3.8+

---

## 🧪 Test Nhanh

Dùng file test 4 cảnh:

```bash
# Sửa generate_prompts.py dòng 9
SCENES_FILE = "scenes_test.txt"

# Chạy
python generate_prompts.py
python translate_prompts.py
```

---

## 🎨 Ví Dụ Output

### **English Prompt (final_prompts_en.txt)**

```
English prompt: {"scene_number":1,"scene_title":"Rooftop Surveillance",...}
English prompt: {"scene_number":2,"scene_title":"Reading Message",...}
```

### **Vietnamese Prompt (final_prompts_vi.txt)**

```
Vietnamese prompt: {"scene_number":1,"scene_title":"Quan Sát Từ Mái Nhà",...}
Vietnamese prompt: {"scene_number":2,"scene_title":"Đọc Tin Nhắn",...}
```

---

## 📚 Tham Khảo

- Tài liệu: `TAI-LIEU-TOOL-PROMPT.txt`
- Model: Gemini 2.5 Flash
- Output format: JSON 1 dòng (no line breaks)

---

## 🐛 Troubleshooting

**Lỗi: Không tìm thấy API key**
→ Kiểm tra `api_keys.txt` có tồn tại và có ít nhất 1 key

**Lỗi: Tất cả API key đều lỗi**
→ Kiểm tra quota của các key tại [Google AI Studio](https://aistudio.google.com)

**Lỗi: File không tồn tại**
→ Đảm bảo chạy script từ thư mục `GITHUB/`

---

## 📄 License

MIT License - Free to use

---

**Tác giả:** FilmAI Team
**Version:** 2.0
**Last Updated:** 2025-11-16
