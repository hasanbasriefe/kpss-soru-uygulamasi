import os
import json
import random
import re
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

def clean_json_response(raw_text):
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

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

    dersler_str = ", ".join(selected_dersler)
    prompt = f"""
Sen OSYM KPSS Ortaogretim soru hazirlama komisyonundasin.
Asagidaki derslerden toplam tam olarak {count} adet benzersiz soru hazirla:
Dersler: {dersler_str}

Kurallar:
- KPSS Ortaogretim duzeyine tam uygun sorular uret.
- Eger Guncel Bilgiler varsa Turkiye ve dunya gundeminden sor.
- 5 secenek (A, B, C, D, E) ve tek dogru cevap olsun.
- Yaniti SADECE gecerli bir JSON dizisi (array) olarak dondur.

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
        }]
    }

    # Yeni nesil API anahtarlari icin acik olan aktif modeller
    active_models = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]

    for model in active_models:
        url = get_endpoint_url(model)
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=50)
            if res.status_code == 200:
                res_data = res.json()
                raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                cleaned_text = clean_json_response(raw_text)
                questions = json.loads(cleaned_text)

                for i, q in enumerate(questions):
                    q["id"] = random.randint(10000, 99999) + i

                print(f"Basarili ({model}): {len(questions)} adet soru uretildi.")
                return questions
            else:
                print(f"Model Denemesi ({model}) [{res.status_code}]: {res.text[:100]}")
        except Exception as e:
            print(f"Istek hatasi: {e}")
            continue

    return []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/get-test", methods=["POST"])
def get_test():
    data = request.json or {}
    selected_dersler = data.get("dersler", ["Güncel Bilgiler"])
    try:
        total_count = int(data.get("soruSayisi", 5))
    except:
        total_count = 5

    questions = generate_ai_questions_rest(selected_dersler, total_count)

    if not questions:
        print(f"API yanit vermedi; yerel havuzdan {total_count} soru tamamlaniyor.")
        pool = load_local_questions()
        filtered = [q for q in pool if q.get("ders") in selected_dersler] or pool
        questions = []
        while len(questions) < total_count and filtered:
            item = random.choice(filtered).copy()
            item["id"] = random.randint(1000, 9999)
            questions.append(item)

    return jsonify({"questions": questions})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
