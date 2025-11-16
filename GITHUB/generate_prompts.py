import google.generativeai as gen
import json

# ==============================
# CẤU HÌNH TÊN FILE
# ==============================

API_KEYS_FILE = "api_keys.txt"               # Mỗi dòng 1 API key
SCENES_FILE = "scenes.txt"                   # Chứa các cảnh: Scene 1: ..., Scene 2: ...
OUTPUT_FILE = "output_prompts.txt"           # Mỗi dòng 1 JSON prompt
CHARACTER_DICT_FILE = "character_dictionary.json"  # Dictionary nhân vật


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
# 3. LOAD CHARACTER DICTIONARY
# ==============================

def load_character_dictionary(path: str = CHARACTER_DICT_FILE):
    """
    Đọc character dictionary từ file JSON.
    Trả về dict với key = tên nhân vật, value = thông tin chi tiết.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        characters = {}
        for char in data.get("characters", []):
            characters[char["name"]] = {
                "name": char["name"],
                "name_closeup": char.get("name_closeup", char["name"] + "2"),
                "appearance": char["appearance"],
                "voice_tone": char["voice_tone"]
            }
        print(f"👥 Đã nạp {len(characters)} nhân vật từ {CHARACTER_DICT_FILE}")
        return characters
    except FileNotFoundError:
        print(f"⚠️ Không tìm thấy {CHARACTER_DICT_FILE}, tiếp tục mà không có character lock")
        return {}
    except Exception as e:
        print(f"⚠️ Lỗi đọc character dictionary: {e}")
        return {}


character_dict = load_character_dictionary()


# ==============================
# 4. PROMPT TEMPLATE
# ==============================

# Dùng placeholder <<SCENE>> và <<CHAR_DICT>> để tránh lỗi .format với dấu {}
PROMPT_TEMPLATE = """
You are a cinematic formatter with character consistency system.

CHARACTER DICTIONARY (use these exact appearances):
<<CHAR_DICT>>

Convert the following scene into ONE SINGLE LINE JSON, EXACTLY in this structure:

{"scene_number":1,"scene_title":"[Short title]","character":{"name":"[Main character name]","appearance":"[Use EXACT appearance from CHARACTER DICTIONARY above]","emotions":{"primary":"[Primary emotion]","secondary":"[Secondary emotion]"},"voice_tone":"[Use EXACT voice_tone from CHARACTER DICTIONARY]"},"setting":{"location":"[Place]","environment":"[Environment]","time":"[Day/Night]"},"cinematic":{"camera":"[Camera shot + movement - auto-select based on scene context]","shot_type":"[wide/medium/close-up/extreme close-up]","focus_characters":["[character names in this shot]"],"lighting":"[Lighting - auto-select]","mood":"[Mood]","style":"Cinematic 8K realistic","effects":"[Effects - auto-select]","sound":"[Ambience]"},"dialogue":{"characters":[{"speaker":"[Speaker name]","line":"[Dialogue line]"}]},"action_block":{"length":"150-200 words","content":"[Cinematic action description]"}}

CRITICAL RULES:

1. CHARACTER CONSISTENCY:
   - ALWAYS use the EXACT "appearance" and "voice_tone" from the CHARACTER DICTIONARY above
   - For character name: use the original name (Alex, Maya, Marcus)
   - DO NOT modify appearance descriptions

2. CLOSE-UP DETECTION & NAME SWITCHING:
   - If shot_type is "close-up" or "extreme close-up":
     * In "focus_characters" array, change names: Alex → Alex2, Maya → Maya2, Marcus → Marcus2
     * If multiple characters in close-up, change ALL their names (e.g., ["Alex2", "Maya2"])
   - If shot_type is "wide" or "medium":
     * Keep original names in "focus_characters" (e.g., ["Alex", "Maya"])

3. AI AUTO-SELECT (choose based on scene context):
   - "camera": Select appropriate camera angle and movement
   - "shot_type": Determine if wide/medium/close-up/extreme close-up
   - "lighting": Choose lighting that fits the mood
   - "effects": Add cinematic effects if needed

4. OUTPUT FORMAT:
   - Return ONLY valid JSON
   - JSON MUST be ONE SINGLE LINE (no line breaks)
   - action_block MUST be 150-200 words

SCENE TO PROCESS:
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

    # Tạo character dictionary string để chèn vào prompt
    char_dict_str = ""
    if character_dict:
        char_dict_str = "\n".join([
            f"- {name}: appearance=\"{info['appearance']}\", voice_tone=\"{info['voice_tone']}\", closeup_name=\"{info['name_closeup']}\""
            for name, info in character_dict.items()
        ])
    else:
        char_dict_str = "(No character dictionary loaded - AI will infer appearances)"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        for idx, scene in enumerate(scenes, start=1):
            print(f"⏳ Đang xử lý cảnh {idx}/{len(scenes)}...")

            # Ghép character dictionary và cảnh vào template
            full_prompt = PROMPT_TEMPLATE.replace("<<CHAR_DICT>>", char_dict_str)
            full_prompt = full_prompt.replace("<<SCENE>>", scene)

            # Gọi Gemini để sinh JSON 1 dòng
            json_line = call_gemini(full_prompt)

            # Ghi mỗi JSON = 1 dòng trong file .txt
            out_f.write(json_line + "\n")

    print(f"\n✅ Xong! Đã lưu {len(scenes)} prompt vào {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
