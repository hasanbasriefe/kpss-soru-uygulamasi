import os
import json
import random
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# Render veya yerel ortamdan API anahtarını alıyoruz
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

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

def generate_ai_questions_batch(selected_dersler, count):
    """
    Seçilen derslerden belirlenen adette KPSS Ortaöğretim formatında
    gerçek ve kaliteli soruları Gemini API ile tek seferde üretir.
    """
    if not GEMINI_API_KEY:
        return []

    prompt = f"""
    Sen ÖSYM standartlarında soru hazırlayan kıdemli bir KPSS Ortaöğretim komisyon uzmanısın.
    Aşağıdaki kurallara göre tam olarak {count} adet soru hazırla.

    Seçilen Dersler: {', '.join(selected_dersler)}
    
    Özel Kurallar:
    1. Sorular KPSS Ortaöğretim seviyesine ve ÖSYM'nin soru mantığına kesinlikle uygun olmalıdır.
    2. Seçenekler 5 şıklı (A, B, C, D, E) olmalı, sadece tek bir doğru cevap bulunmalıdır.
    3. Eğer seçilen dersler arasında 'Güncel Bilgiler' varsa; UNESCO Dünya Mirası listeleri, uluslararası kuruluşlar, önemli edebiyat/sanat eserleri, bilim-uzay gelişmeleri ve genel kültür konularından soru üret. Asla uydurma veya 'tanım' gibi jenerik ifadeler kullanma.
    4. Her soru için doyurucu, öğretici bir çözüm gerekçesi yaz.
    5. Ürettiğin soruları seçilen derslere dengeli biçimde dağıt.

    Cevabını yalnızca ve yalnızca aşağıdaki JSON şemasına uygun bir liste (array) olarak döndür:
    [
      {{
        "id": 1,
        "ders": "Ders Adı",
        "soru": "Soru metni...",
        "secenekler": [
          "A) ...",
          "B) ...",
          "C) ...",
          "D) ...",
          "E) ..."
        ],
        "dogruCevap": "A",
        "cozum": "Açıklayıcı ve net çözüm gerekçesi..."
      }}
    ]
    """

    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )
        response = model.generate_content(prompt)
        questions = json.loads(response.text)
        
        # ID'leri rastgele benzersiz yapalım
        for i, q in enumerate(questions):
            q["id"] = random.randint(10000, 99999) + i
            
        return questions
    except Exception as e:
        print(f"Gemini API Hatası: {e}")
        return []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/get-test", methods=["POST"])
def get_test():
    data = request.json or {}
    selected_dersler = data.get("dersler", [])
    total_count = int(data.get("soruSayisi", 5))

    # Önce yapay zekadan taze ve yeni sorular üretmeyi dene
    ai_questions = generate_ai_questions_batch(selected_dersler, total_count)

    if ai_questions and len(ai_questions) > 0:
        return jsonify({"questions": ai_questions})

    # Eğer API kotası dolarsa veya anahtar girilmemişse yerel havuzdan tamamla (Yedek Plan)
    pool = load_local_questions()
    filtered = [q for q in pool if q.get("ders") in selected_dersler]
    random.shuffle(filtered)

    selected_questions = filtered[:total_count]
    return jsonify({"questions": selected_questions})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
