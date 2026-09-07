import os
import json
import random
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "questions.json")

def load_local_questions():
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"JSON Okuma Hatası: {e}")
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

def generate_ai_questions_rest(selected_dersler, count):
    if not GEMINI_API_KEY:
        print("API Hatası: GEMINI_API_KEY bulunamadı!")
        return []

    dersler_str = ", ".join(selected_dersler)
    prompt = f"""
Sen ÖSYM KPSS Ortaöğretim soru hazırlama komisyonundasın.
Aşağıdaki derslerden toplam tam olarak {count} adet benzersiz ve kaliteli soru hazırla:
Dersler: {dersler_str}

Kurallar:
- Klişe olmayan, özgün ve KPSS Ortaöğretim düzeyine tam uygun sorular üret.
- Eğer Güncel Bilgiler varsa; Türkiye ve dünya gündemi, UNESCO kültür varlıkları, edebiyat, sanat ve spor gelişmelerinden sor.
- 5 seçenek (A, B, C, D, E) ve tek bir doğru cevap olsun.
- Yanıtı SADECE geçerli bir JSON dizisi (array) olarak döndür. Başka hiçbir açıklama yazma.

Format Şablonu:
[
  {{
    "ders": "Ders Adı",
    "soru": "Soru metni...",
    "secenekler": ["A) ...", "B) ...", "C) ...", "D) ...", "E) ..."],
    "dogruCevap": "A",
    "cozum": "Açıklayıcı gerekçe..."
  }}
]
"""

    url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=){GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=45)
        res_data = res.json()

        if res.status_code != 200:
            print(f"Google REST API Hatası ({res.status_code}): {res.text}")
            return []

        raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
        cleaned_text = clean_json_response(raw_text)
        questions = json.loads(cleaned_text)

        for i, q in enumerate(questions):
            q["id"] = random.randint(10000, 99999) + i

        print(f"Başarılı: {len(questions)} adet yapay zeka sorusu üretildi.")
        return questions

    except Exception as e:
        print(f"Soru üretim hatası: {e}")
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
        print(f"API yanıt vermedi; yerel havuzdan {total_count} soru tamamlanıyor.")
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
