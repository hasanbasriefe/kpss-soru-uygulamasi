import os
import json
import random
from flask import Flask, render_template, request, jsonify
from google import genai

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = None

if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY.strip())
    except Exception as e:
        print(f"Client başlatma hatası: {e}")

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

def generate_ai_questions(selected_dersler, count):
    if not client:
        print("API Hatası: Client veya API Anahtarı aktif değil.")
        return []

    dersler_str = ", ".join(selected_dersler)
    prompt = f"""
    Sen ÖSYM KPSS Ortaöğretim soru hazırlama komisyonundasın.
    Aşağıdaki derslerden toplam tam olarak {count} adet benzersiz ve kaliteli soru hazırla:
    Dersler: {dersler_str}

    Kurallar:
    - Klişe olmayan, özgün ve KPSS Ortaöğretim düzeyinde sorular üret.
    - Eğer Güncel Bilgiler varsa; Türkiye ve dünya gündemi, UNESCO kültür varlıkları, edebiyat, sanat ve spor gelişmelerinden sor.
    - 5 seçenek (A, B, C, D, E) ve tek bir doğru cevap olsun.
    - Yanıtı SADECE geçerli bir JSON dizisi (array) olarak döndür. Markdown etiketleri dışında hiçbir metin yazma.

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

    # Hata çıktısında belirtilen güncel modeller:
    models_to_try = ["gemini-2.5-flash", "gemini-2.5-pro"]

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            cleaned_text = clean_json_response(response.text)
            questions = json.loads(cleaned_text)

            for i, q in enumerate(questions):
                q["id"] = random.randint(10000, 99999) + i

            print(f"Başarılı ({model_name}): {len(questions)} adet yapay zeka sorusu üretildi.")
            return questions
        except Exception as e:
            print(f"{model_name} denenirken hata: {e}")
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

    questions = generate_ai_questions(selected_dersler, total_count)

    if not questions:
        print(f"API devre dışı kaldı; questions.json üzerinden {total_count} soru tamamlanıyor.")
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
