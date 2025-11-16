import google.generativeai as gen

# ==============================
# CẤU HÌNH TÊN FILE
# ==============================

API_KEYS_FILE = "api_keys.txt"        # Mỗi dòng 1 API key
SCENES_FILE = "scenes.txt"            # Chứa các cảnh: Scene 1: ..., Scene 2: ...
OUTPUT_FILE = "output_prompts.txt"    # Mỗi dòng 1 JSON prompt


# ==============================
# 1. LOAD API KEYS
# ==============================

def load_api_keys(path: str = API_KEYS_FILE):
    """Đọc danh sách API key (mỗi dòng 1 key)."""
    with open(path, "r", encoding="utf-8") as f:
        keys = [line.strip() for line in f if line.strip()]
    if not keys:
        raise Exception("❌ Không tìm thấy API key nào trong api_keys.txt")
    return keys


API_KEYS = load_api_keys()
current_key_index = 0


def set_current_key():
    """Cấu hình API key hiện tại cho Gemini."""
    gen.configure(api_key=API_KEYS[current_key_index])
    print(f"🔑 Đang dùng API key #{current_key_index + 1}")


set_current_key()


def switch_key():
    """Đổi sang API key kế tiếp khi key hiện tại lỗi / hết quota."""
    global current_key_index
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    set_current_key()


# ==============================
# 2. LOAD SCENES
# ==============================

def load_scenes(path: str = SCENES_FILE):
    """
    Đọc file scenes.txt và tách thành từng cảnh.
    Yêu cầu format:
        Scene 1: ...
        
        Scene 2: ...
        ...
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        return []

    blocks = []
    parts = text.split("Scene ")
    for part in parts[1:]:
        # part dạng: "1: nội dung..." hoặc "2: nội dung..."
        if ":" not in part:
            continue
        num, rest = part.split(":", 1)
        num = num.strip()
        content = rest.strip()
        if not content:
            continue
        blocks.append(f"Scene {num}: {content}")

    return blocks


scenes = load_scenes()
print(f"📚 Đã nạp {len(scenes)} cảnh từ {SCENES_FILE}")


# ==============================
# 3. PROMPT TEMPLATE
# ==============================

# Dùng placeholder <<SCENE>> để tránh lỗi .format với dấu {}
PROMPT_TEMPLATE = """
You are a cinematic formatter.
Convert the following scene into ONE SINGLE LINE JSON, EXACTLY in this structure:

{"scene_number":1,"scene_title":"[Short title]","character":{"name":"[Main character]","appearance":"[Appearance]","emotions":{"primary":"[Primary emotion]","secondary":"[Secondary emotion]"},"voice_tone":"[Voice tone]"},"setting":{"location":"[Place]","environment":"[Environment]","time":"[Day/Night]"},"cinematic":{"camera":"[Camera shot + movement]","lighting":"[Lighting]","mood":"[Mood]","style":"Cinematic 8K realistic","effects":"[Effects]","sound":"[Ambience]"},"dialogue":{"characters":[{"speaker":"[Speaker]","line":"[Dialogue line]"}]},"action_block":{"length":"150-200 words","content":"[Cinematic action description]"}}

RULES:
- Return ONLY valid JSON.
- JSON MUST be ONE SINGLE LINE (no line breaks).
- Infer missing details logically.
- action_block MUST be 150-200 words.

SCENE:
\"\"\"<<SCENE>>\"\"\"
"""


# ==============================
# 4. GỌI GEMINI VỚI XOAY API
# ==============================

def call_gemini(prompt: str) -> str:
    """
    Gọi Gemini với nội dung prompt.
    Nếu 1 API key lỗi / hết quota → tự động đổi sang API key khác.
    """
    global current_key_index

    for _ in range(len(API_KEYS)):
        try:
            # Dùng đúng model mà bạn đang dùng trong tool: models/gemini-2.5-flash
            model = gen.GenerativeModel("models/gemini-2.5-flash")
            resp = model.generate_content(prompt)

            # Lấy text, xoá xuống dòng → ép thành 1 dòng
            text = (resp.text or "").strip()
            one_line = " ".join(text.splitlines()).strip()
            return one_line

        except Exception as e:
            print(f"⚠️ Lỗi với key #{current_key_index + 1}: {e}")
            print("🔄 Đổi sang API key tiếp theo...")
            switch_key()

    # Nếu chạy hết vòng mà tất cả key đều lỗi
    raise Exception("❌ Tất cả API key đều lỗi hoặc hết quota.")


# ==============================
# 5. CHẠY QUA TỪNG CẢNH & LƯU RA FILE
# ==============================

def main():
    if not scenes:
        print("⚠️ Không có cảnh nào trong scenes.txt – kiểm tra lại file input.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        for idx, scene in enumerate(scenes, start=1):
            print(f"⏳ Đang xử lý cảnh {idx}/{len(scenes)}...")

            # Ghép cảnh vào template
            full_prompt = PROMPT_TEMPLATE.replace("<<SCENE>>", scene)

            # Gọi Gemini để sinh JSON 1 dòng
            json_line = call_gemini(full_prompt)

            # Ghi mỗi JSON = 1 dòng trong file .txt
            out_f.write(json_line + "\n")

    print(f"\n✅ Xong! Đã lưu {len(scenes)} prompt vào {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
