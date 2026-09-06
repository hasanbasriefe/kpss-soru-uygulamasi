import os
import json
import random
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# Çevre değişkeninden API anahtarını alıyoruz
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY.strip())
else:
    print("UYARI: GEMINI_API_KEY ortam değişkeni bulunamadı!")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "questions.json")

def load_local_questions():
    """Yedek JSON havuzunu güvenli biçimde okur."""
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"JSON Okuma Hatası: {e}")
    return []

def clean_json_response(raw_text):
    """Yapay zekanın ürettiği metindeki markdown etiketlerini temizler."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def generate_ai_questions(selected_dersler, count):
    """Gemini API ile KPSS Ortaöğretim seviyesinde özgün soru üretir."""
    if not GEMINI_API_KEY:
        print("Hata: GEMINI_API_KEY tanımlanmamış!")
        return []

    dersler_str = ", ".join(selected_dersler)
    prompt = f"""
    Sen ÖSYM KPSS Ortaöğretim soru hazırlama komisyonundasın.
    Aşağıdaki derslerden toplam tam olarak {count} adet benzersiz soru hazırla:
    Dersler: {dersler_str}

    Kurallar:
    - Kesinlikle klişe olmayan, KPSS Ortaöğretim düzeyine uygun, kaliteli sorular üret.
    - Eğer Güncel Bilgiler dersi varsa; Türkiye ve dünya gündemi, UNESCO kültür mirası, edebiyat, sanat, tarih ve uluslararası teşkilat konularına yer ver.
    - Her soruda 5 seçenek (A, B, C, D, E) ve tek bir doğru cevap bulunmalıdır.
    - Her soruya doyurucu bir çözüm açıklaması ekle.
    - SADECE aşağıdaki JSON şemasına uygun bir dizi (array) döndür. Asla fazladan metin yazma.

    Format Şablonu:
    [
      {{
        "ders": "Ders Adı",
        "soru": "Soru metni",
        "secenekler": ["A) ...", "B) ...", "C) ...", "D) ...", "E) ..."],
        "dogruCevap": "A",
        "cozum": "Çözüm açıklaması"
      }}
    ]
    """

    # 404 hatasını önlemek için aktif modeller sırayla denenir
    candidate_models = [
        "gemini-1.5-flash-latest",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash"
    ]

    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            cleaned_text = clean_json_response(response.text)
            questions = json.loads(cleaned_text)

            for i, q in enumerate(questions):
                q["id"] = random.randint(10000, 99999) + i

            print(f"Başarılı ({model_name}): {len(questions)} adet yapay zeka sorusu üretildi.")
            return questions
        except Exception as e:
            print(f"Model Denemesi Başarısız ({model_name}): {e}")
            continue

    print("Hata: Hiçbir modelden geçerli soru üretilemedi.")
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
    except (ValueError, TypeError):
        total_count = 5

    # 1. Öncelik: Gemini API
    questions = generate_ai_questions(selected_dersler, total_count)

    # 2. Öncelik (Yedek Plan): API yanıt vermezse JSON havuzundan karşıla
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
