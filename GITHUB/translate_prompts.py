import google.generativeai as gen
import json

# ==============================
# CẤU HÌNH TÊN FILE
# ==============================

API_KEYS_FILE = "api_keys.txt"
INPUT_FILE = "output_prompts.txt"         # JSON từ Node 2
OUTPUT_EN_FILE = "final_prompts_en.txt"   # Tiếng Anh
OUTPUT_VI_FILE = "final_prompts_vi.txt"   # Tiếng Việt


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
# 2. LOAD PROMPTS TỪ NODE 2
# ==============================

def load_prompts(path: str = INPUT_FILE):
    """
    Đọc file output từ Node 2.
    Mỗi dòng là 1 JSON prompt.
    """
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    print(f"📚 Đã nạp {len(lines)} prompt từ {INPUT_FILE}")
    return lines


prompts = load_prompts()


# ==============================
# 3. TRANSLATION PROMPT
# ==============================

TRANSLATE_PROMPT = """
You are a professional translator specializing in cinematic content.

Translate the following JSON prompt from ENGLISH to VIETNAMESE.

RULES:
1. Translate ALL text fields to Vietnamese (scene_title, character names, dialogue, action_block, etc.)
2. Keep the JSON structure EXACTLY the same
3. Keep technical terms in English: "Cinematic 8K realistic", camera angles, lighting terms
4. Return ONLY the translated JSON on ONE SINGLE LINE (no line breaks)
5. Ensure the translation is natural and cinematic in Vietnamese

ORIGINAL JSON:
\"\"\"<<JSON>>\"\"\"

Return only the Vietnamese JSON, nothing else.
"""


# ==============================
# 4. GỌI GEMINI ĐỂ DỊCH
# ==============================

def translate_to_vietnamese(json_str: str) -> str:
    """
    Dịch JSON prompt từ tiếng Anh sang tiếng Việt.
    """
    global current_key_index

    for _ in range(len(API_KEYS)):
        try:
            model = gen.GenerativeModel("models/gemini-2.5-flash")
            prompt = TRANSLATE_PROMPT.replace("<<JSON>>", json_str)
            resp = model.generate_content(prompt)

            # Lấy text, xoá xuống dòng → ép thành 1 dòng
            text = (resp.text or "").strip()
            # Loại bỏ markdown code blocks nếu có
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

    # Nếu chạy hết vòng mà tất cả key đều lỗi
    raise Exception("❌ Tất cả API key đều lỗi hoặc hết quota.")


# ==============================
# 5. XỬ LÝ & LƯU FILE
# ==============================

def main():
    if not prompts:
        print("⚠️ Không có prompt nào trong output_prompts.txt")
        return

    print("\n🌍 Bắt đầu xử lý EN/VI...")

    # Mở cả 2 file output
    with open(OUTPUT_EN_FILE, "w", encoding="utf-8") as en_f, \
         open(OUTPUT_VI_FILE, "w", encoding="utf-8") as vi_f:

        for idx, prompt_json in enumerate(prompts, start=1):
            print(f"⏳ Đang xử lý prompt {idx}/{len(prompts)}...")

            # 1. Lưu bản tiếng Anh (giữ nguyên)
            en_f.write(f"English prompt: {prompt_json}\n")

            # 2. Dịch sang tiếng Việt
            try:
                vi_json = translate_to_vietnamese(prompt_json)
                vi_f.write(f"Vietnamese prompt: {vi_json}\n")
            except Exception as e:
                print(f"❌ Lỗi dịch prompt {idx}: {e}")
                vi_f.write(f"Vietnamese prompt: [TRANSLATION ERROR]\n")

    print(f"\n✅ Xong! Đã lưu:")
    print(f"   - {len(prompts)} prompts tiếng Anh → {OUTPUT_EN_FILE}")
    print(f"   - {len(prompts)} prompts tiếng Việt → {OUTPUT_VI_FILE}")


if __name__ == "__main__":
    main()
