import os
import json
import random
import re
import time
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

RAW_KEY = os.environ.get("GEMINI_API_KEY", "")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "questions.json")

def load_local_questions():
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"JSON Okuma Hatasi: {e}")
    return []

def extract_json_array(raw_text):
    """Metin içindeki geçerli JSON dizisini ([...]) çeker, bozuk uç kısımları temizler."""
    text = raw_text.strip()
    match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass
    
    # Markdown blok temizliği
    if "```json" in text:
        text = text.split("```json")[-1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1]
    
    try:
        return json.loads(text.strip())
    except Exception as e:
        print(f"JSON parse hatasi: {e}")
        return []

def get_clean_key():
    val = str(RAW_KEY).strip()
    match = re.search(r"AQ\.[a-zA-Z0-9_\-]+", val)
    if match:
        return match.group(0)
    for ch in ["[", "]", "(", ")", "'", '"', " "]:
        val = val.replace(ch, "")
    if "key=" in val:
        val = val.split("key=")[-1]
    return val.strip()

def get_endpoint_url(model_name):
    scheme = "".join([chr(104), chr(116), chr(116), chr(112), chr(115)])
    colon_slash = chr(58) + chr(47) + chr(47)
    host = "generativelanguage.googleapis.com"
    endpoint = f"v1beta/models/{model_name}:generateContent"
    return f"{scheme}{colon_slash}{host}/{endpoint}"

def generate_ai_questions_rest(selected_dersler, count):
    api_key = get_clean_key()
    if not api_key:
        print("API Hatasi: GEMINI_API_KEY bos!")
        return []

    # Kota ve token limitine takılmamak için tek seferde en fazla 10 soru üret
    actual_count = min(count, 10)
    dersler_str = ", ".join(selected_dersler)

    prompt = f"""
Sen OSYM KPSS Ortaogretim soru hazirlama komisyonundasin.
Asagidaki derslerden toplam tam olarak {actual_count} adet benzersiz soru hazirla:
Dersler: {dersler_str}

Kurallar:
- KPSS Ortaogretim duzeyine uygun, guncel ve ozgun sorular yaz.
- 5 secenek (A, B, C, D, E) ve tek dogru cevap olsun.
- Yaniti SADECE gecerli bir JSON dizisi olarak ver. Markdown disinda yazi yazma.

Format:
[
  {{
    "ders": "Ders Adi",
    "soru": "Soru metni...",
    "secenekler": ["A) ...", "B) ...", "C) ...", "D) ...", "E) ..."],
    "dogruCevap": "A",
    "cozum": "Aciklama..."
  }}
]
"""

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4096
        }
    }

    models_to_try = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-1.5-flash"]

    for model in models_to_try:
        url = get_endpoint_url(model)
        for attempt in range(2):
            try:
                res = requests.post(url, headers=headers, json=payload, timeout=30)
                if res.status_code == 200:
                    res_data = res.json()
                    raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                    questions = extract_json_array(raw_text)

                    if questions:
                        for i, q in enumerate(questions):
                            q["id"] = random.randint(10000, 99999) + i
                        print(f"Basarili ({model}): {len(questions)} adet soru uretildi.")
                        return questions
                elif res.status_code == 429:
                    print(f"Kota siniri (429) alindi, 2 saniye bekleniyor... ({model})")
                    time.sleep(2)
                else:
                    print(f"Model ({model}) [{res.status_code}]: {res.text[:80]}")
                    break
            except Exception as e:
                print(f"Istek hatasi ({model}): {e}")
                break

    return []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/get-test", methods=["POST"])
def get_test():
    try:
        data = request.json or {}
        selected_dersler = data.get("dersler", ["Güncel Bilgiler"])
        try:
            total_count = int(data.get("soruSayisi", 5))
        except:
            total_count = 5

        # 1. Yapay zekadan taze soru iste
        questions = generate_ai_questions_rest(selected_dersler, total_count)

        # 2. Kota dolmussa yerel havuzdan tamamla
        if not questions:
            print("API kota nedeniyle yanit veremedi, yerel havuz devreye giriyor.")
            pool = load_local_questions()
            filtered = [q for q in pool if q.get("ders") in selected_dersler] or pool

            if filtered:
                questions = []
                for i in range(total_count):
                    item = random.choice(filtered).copy()
                    item["id"] = random.randint(1000, 9999) + i
                    questions.append(item)

        return jsonify({"questions": questions or []})
    except Exception as err:
        print(f"Sunucu Hatasi: {err}")
        return jsonify({"questions": []}), 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
