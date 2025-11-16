import google.generativeai as gen
import json
import random
from pathlib import Path

# ==============================
# CẤU HÌNH TÊN FILE
# ==============================

API_KEYS_FILE = "api_keys.txt"                     # Mỗi dòng 1 API key
SCENES_FILE = "scenes.txt"                         # Danh sách scene
OUTPUT_FILE = "output_prompts.txt"                 # Kết quả JSON lines
CHARACTER_DICT_FILE = "character_dictionary.json"  # Dictionary nhân vật
CAMERA_STYLES_FILE = "camera_styles.txt"           # Danh sách camera cinematic


# ==============================
# 1. LOAD API KEYS
# ==============================

def load_api_keys(path: str = API_KEYS_FILE):
    """Đọc danh sách API key (mỗi dòng 1 key)."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Không tìm thấy {path}")
    keys = [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not keys:
        raise ValueError("❌ Không có API key nào trong api_keys.txt")
    print(f"🔑 Đã nạp {len(keys)} API key.")
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
    Format gợi ý:
        Scene 16: ...
        Scene 17: ...
    """
    p = Path(path)
    if not p.exists():
        print(f"⚠️ Không tìm thấy {path}")
        return []

    text = p.read_text(encoding="utf-8").strip()
    if not text:
        return []

    blocks = []
    parts = text.split("Scene ")
    for part in parts[1:]:
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
    Trả về dict:
        {
          "Alex": { "name": "Alex", "name_closeup": "Alex2", "appearance": "...", "voice_tone": "..." },
          ...
        }
    """
    p = Path(path)
    if not p.exists():
        print(f"⚠️ Không tìm thấy {path}, tiếp tục mà không có character lock.")
        return {}

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"⚠️ Lỗi đọc/parse {path}: {e}")
        return {}

    characters = {}
    for char in data.get("characters", []):
        name = char.get("name")
        if not name:
            continue
        characters[name] = {
            "name": name,
            "name_closeup": char.get("name_closeup", name + "2"),
            "appearance": char.get("appearance", ""),
            "voice_tone": char.get("voice_tone", ""),
        }

    print(f"👥 Đã nạp {len(characters)} nhân vật từ {CHARACTER_DICT_FILE}")
    return characters


character_dict = load_character_dictionary()

# Reverse map cho closeup_name -> base_name (nếu sau này cần)
reverse_closeup_map = {}
for base_name, info in character_dict.items():
    close_name = info.get("name_closeup")
    if close_name:
        reverse_closeup_map[close_name] = base_name


def build_fixed_character_definitions():
    """
    Tạo block fixed_character_definitions để gắn vào mỗi prompt.
    Structure:
    "fixed_character_definitions": {
       "Alex": {"appearance": "...", "voice_tone": "...", "name_closeup": "Alex2"},
       ...
    }
    """
    fixed = {}
    for name, info in character_dict.items():
        fixed[name] = {
            "appearance": info.get("appearance", ""),
            "voice_tone": info.get("voice_tone", ""),
            "name_closeup": info.get("name_closeup", name + "2"),
        }
    return fixed


fixed_character_definitions = build_fixed_character_definitions()


# ==============================
# 4. LOAD CAMERA STYLES
# ==============================

def load_camera_styles(path: str = CAMERA_STYLES_FILE):
    """
    Đọc danh sách camera từ file .txt, bỏ dòng trống và dòng bắt đầu bằng '#'.
    """
    p = Path(path)
    if not p.exists():
        print(f"⚠️ Không tìm thấy {path}, AI sẽ tự chọn camera.")
        return []

    lines = p.read_text(encoding="utf-8").splitlines()
    cameras = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cameras.append(line)

    print(f"🎥 Đã nạp {len(cameras)} kiểu camera từ {CAMERA_STYLES_FILE}")
    return cameras


camera_styles = load_camera_styles()

# Biến toàn cục dùng để chống trùng giữa các cảnh
last_camera = None
last_shot_type = None


# ==============================
# 5. PROMPT TEMPLATE GỬI CHO GEMINI
# ==============================

PROMPT_TEMPLATE = """
You are a cinematic formatter with a character consistency system.

CHARACTER DICTIONARY (use these exact appearances):
<<CHAR_DICT>>

CAMERA STYLE OPTIONS (use EXACTLY one of these values for the "camera" field):
<<CAMERA_LIST>>

Convert the following scene into ONE SINGLE LINE JSON, EXACTLY in this structure:

{"scene_number":1,"scene_title":"[Short title]","character":{"name":"[Main character name]","appearance":"[Use EXACT appearance from CHARACTER DICTIONARY above]","emotions":{"primary":"[Primary emotion]","secondary":"[Secondary emotion]"},"voice_tone":"[Use EXACT voice_tone from CHARACTER DICTIONARY]"},"setting":{"location":"[Place]","environment":"[Environment]","time":"[Day/Night]"},"cinematic":{"camera":"[One camera style from CAMERA STYLE OPTIONS above]","shot_type":"[wide/medium/close-up/extreme close-up]","focus_characters":["[character names in this shot]"],"lighting":"[Lighting - auto-select]","mood":"[Mood]","style":"Cinematic 8K realistic","effects":"[Effects - auto-select]","sound":"[Ambience]"},"dialogue":{"characters":[{"speaker":"[Speaker name]","line":"[Dialogue line]"}]},"action_block":{"length":"150-200 words","content":"[Cinematic action description]"}}

CRITICAL RULES:

1. CHARACTER CONSISTENCY:
   - ALWAYS use the EXACT "appearance" and "voice_tone" from the CHARACTER DICTIONARY above
   - For character name: use the original base names (Alex, Maya, Marcus)
   - DO NOT modify appearance descriptions

2. CLOSE-UP DETECTION & NAME SWITCHING:
   - If shot_type is "close-up" or "extreme close-up":
     * In "focus_characters" array, change names: Alex → Alex2, Maya → Maya2, Marcus → Marcus2
     * If multiple characters in close-up, change ALL their names (e.g., ["Alex2", "Maya2"])
   - If shot_type is "wide" or "medium":
     * Keep original names in "focus_characters" (e.g., ["Alex", "Maya"])

3. AI AUTO-SELECT:
   - "camera": MUST be one of the CAMERA STYLE OPTIONS above
   - "shot_type": choose wide/medium/close-up/extreme close-up based on scene emotion and action
   - "lighting": choose lighting that fits the mood
   - "effects": add cinematic effects if needed

4. OUTPUT FORMAT:
   - Return ONLY valid JSON
   - JSON MUST be ONE SINGLE LINE (no line breaks)
   - action_block MUST be 150-200 words

SCENE TO PROCESS:
\"\"\"<<SCENE>>\"\"\"
"""


# ==============================
# 6. GỌI GEMINI VỚI XOAY API KEY
# ==============================

def call_gemini(prompt: str) -> str:
    """
    Gọi Gemini với nội dung prompt.
    Nếu 1 API key lỗi / hết quota → tự động đổi sang API key khác.
    Trả về: 1 dòng JSON string (có thể cần hậu xử lý thêm).
    """
    global current_key_index

    for _ in range(len(API_KEYS)):
        try:
            model = gen.GenerativeModel("models/gemini-2.5-flash")
            resp = model.generate_content(prompt)
            text = (resp.text or "").strip()

            # Loại bỏ markdown code block nếu có
            if text.startswith("```json"):
                text = text.replace("```json", "").replace("```", "").strip()
            elif text.startswith("```"):
                text = text.replace("```", "").strip()

            one_line = " ".join(text.splitlines()).strip()
            return one_line

        except Exception as e:
            print(f"⚠️ Lỗi với key #{current_key_index + 1}: {e}")
            print("🔄 Đổi sang API key tiếp theo...")
            switch_key()

    raise Exception("❌ Tất cả API key đều lỗi hoặc hết quota.")


# ==============================
# 7. HẬU XỬ LÝ: CLOSE-UP LOGIC + CAMERA / SHOT_TYPE
# ==============================

def apply_closeup_and_fixed_defs(data: dict) -> dict:
    """
    - Gắn fixed_character_definitions vào JSON
    - Áp dụng close-up logic: Alex/Maya/Marcus → Alex2/Maya2/Marcus2 nếu shot_type là close-up/extreme close-up
    """
    # 1) fixed_character_definitions
    if fixed_character_definitions:
        data["fixed_character_definitions"] = fixed_character_definitions

    # 2) Close-up logic cho focus_characters
    cinematic = data.get("cinematic", {})
    shot_type = str(cinematic.get("shot_type", "")).strip()
    norm = shot_type.lower().replace(" ", "").replace("-", "")
    is_closeup = norm in ("closeup", "extremecloseup")

    focus = cinematic.get("focus_characters")
    if is_closeup and isinstance(focus, list) and character_dict:
        new_focus = []
        for name in focus:
            if name in character_dict:
                close_name = character_dict[name].get("name_closeup", name + "2")
                new_focus.append(close_name)
            else:
                new_focus.append(name)
        cinematic["focus_characters"] = new_focus

    data["cinematic"] = cinematic
    return data


def postprocess_camera_and_shottype(data: dict) -> dict:
    """
    - Chống trùng camera giữa các cảnh liên tiếp.
    - Hạn chế shot_type bị lặp 1 kiểu hoài (medium, close-up...).
    """
    global last_camera, last_shot_type, camera_styles

    cinematic = data.get("cinematic", {})

    # ----- 1) CAMERA ANTI-REPEAT -----
    cam = cinematic.get("camera")
    if isinstance(cam, str):
        cam_stripped = cam.strip()

        # Nếu AI chế camera không có trong danh sách & có camera_styles thì random 1 cái hợp lệ
        if camera_styles:
            if cam_stripped not in camera_styles:
                cam_stripped = random.choice(camera_styles)
                cinematic["camera"] = cam_stripped

            # Nếu giống cảnh trước → chọn cái khác
            if last_camera is not None and cam_stripped == last_camera:
                alternatives = [c for c in camera_styles if c != last_camera]
                if alternatives:
                    new_cam = random.choice(alternatives)
                    cinematic["camera"] = new_cam
                    cam_stripped = new_cam

        last_camera = cam_stripped

    # ----- 2) SHOT_TYPE ANTI-REPEAT -----
    shot = cinematic.get("shot_type")
    if isinstance(shot, str):
        s = shot.strip().lower()
        base = s.replace("-", "").replace(" ", "")

        # Nếu AI trả linh tinh thì chuẩn hoá về 4 loại chính
        if "close" in base and "extreme" in base:
            base = "extremecloseup"
            cinematic["shot_type"] = "extreme close-up"
        elif "close" in base:
            base = "closeup"
            cinematic["shot_type"] = "close-up"
        elif "wide" in base:
            base = "wide"
            cinematic["shot_type"] = "wide"
        elif "medium" in base:
            base = "medium"
            cinematic["shot_type"] = "medium"

        # Nếu giống loại previous → ép đổi cho đa dạng
        if last_shot_type is not None and base == last_shot_type:
            if base == "medium":
                cinematic["shot_type"] = "close-up"
                base = "closeup"
            elif base in ("closeup", "extremecloseup"):
                cinematic["shot_type"] = "medium"
                base = "medium"
            elif base == "wide":
                cinematic["shot_type"] = "medium"
                base = "medium"

        last_shot_type = base

    data["cinematic"] = cinematic
    return data


def postprocess_json_line(json_line: str) -> str:
    """
    Parse JSON string, áp dụng:
      - fixed_character_definitions
      - close-up logic
      - anti-repeat camera
      - anti-repeat shot_type
    Trả về: JSON string 1 dòng.
    """
    try:
        data = json.loads(json_line)
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON không parse được, ghi raw line. Lỗi: {e}")
        return json_line

    data = apply_closeup_and_fixed_defs(data)
    data = postprocess_camera_and_shottype(data)

    return json.dumps(data, ensure_ascii=False)


# ==============================
# 8. MAIN: CHẠY TỪNG CẢNH & LƯU RA FILE
# ==============================

def main():
    if not scenes:
        print("⚠️ Không có cảnh nào trong scenes.txt – kiểm tra lại file input.")
        return

    # Chuẩn bị CHAR_DICT string cho prompt
    if character_dict:
        char_dict_str = "\n".join([
            f"- {name}: appearance=\"{info.get('appearance','')}\", voice_tone=\"{info.get('voice_tone','')}\", closeup_name=\"{info.get('name_closeup', name + '2')}\""
            for name, info in character_dict.items()
        ])
    else:
        char_dict_str = "(No character dictionary loaded - AI will infer appearances)"

    # Chuẩn bị CAMERA_LIST string cho prompt
    if camera_styles:
        camera_list_str = "\n".join([f"- {c}" for c in camera_styles])
    else:
        camera_list_str = "- tracking shot\n- medium shot\n- wide shot\n- close-up shot"

    out_path = Path(OUTPUT_FILE)
    with out_path.open("w", encoding="utf-8") as out_f:
        for idx, scene in enumerate(scenes, start=1):
            print(f"⏳ Đang xử lý cảnh {idx}/{len(scenes)}...")

            prompt = PROMPT_TEMPLATE.replace("<<CHAR_DICT>>", char_dict_str)
            prompt = prompt.replace("<<CAMERA_LIST>>", camera_list_str)
            prompt = prompt.replace("<<SCENE>>", scene)

            raw_line = call_gemini(prompt)
            final_line = postprocess_json_line(raw_line)

            out_f.write(final_line + "\n")

    print(f"\n✅ Xong! Đã lưu {len(scenes)} prompt vào {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
