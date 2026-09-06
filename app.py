import os
import json
import random
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

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
    if not GEMINI_API_KEY:
        print("Hata: GEMINI_API_KEY bulunamadı!")
        return []

    prompt = f"""
    Sen KPSS Ortaöğretim sınav komisyonu uzmanısın.
    Aşağıdaki kurallara göre EKSİKSİZ TAM OLARAK {count} ADET soru hazırla:

    Seçilen Dersler: {', '.join(selected_dersler)}
    
    Kurallar:
    1. Toplam soru sayısı kesinlikle {count} adet olmalıdır. Ne eksik ne fazla.
    2. Sorular KPSS Ortaöğretim müfredatına uygun, 5 seçenekli (A, B, C, D, E) olmalıdır.
    3. Güncel Bilgiler dersi için UNESCO, tarihî-kültürel yapılar, edebiyat ve güncel uluslararası konular seçilmelidir.
    4. Her soru için açıklayıcı bir çözüm metni ekle.

    Yalnızca aşağıdaki şemaya uygun bir JSON dizisi (array) döndür:
    [
      {{
        "id": 1,
        "ders": "Ders Adı",
        "soru": "Soru metni",
        "secenekler": ["A) ...", "B) ...", "C) ...", "D) ...", "E) ..."],
        "dogruCevap": "A",
        "cozum": "Çözüm açıklaması"
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
        
        for i, q in enumerate(questions):
            q["id"] = random.randint(10000, 99999) + i
            
        return questions
    except Exception as e:
        print(f"Gemini API Çağrısı Başarısız: {e}")
        return []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/get-test", methods=["POST"])
def get_test():
    data = request.json or {}
    selected_dersler = data.get("dersler", [])
    
    # Kullanıcının seçtiği soru sayısını tam sayıya çeviriyoruz
    try:
        total_count = int(data.get("soruSayisi", 10))
    except (ValueError, TypeError):
        total_count = 10

    # 1. Öncelik: Gemini API ile taze soru üret
    questions = generate_ai_questions_batch(selected_dersler, total_count)

    # 2. Öncelik (Yedek Plan): API çalışmazsa yerel havuzdan istenen sayıya ulaşana kadar tamamla
    if not questions or len(questions) == 0:
        print(f"Uyarı: API yanıt vermedi, yerel havuz kullanılıyor. İstenen adet: {total_count}")
        pool = load_local_questions()
        filtered = [q for q in pool if q.get("ders") in selected_dersler] or pool

        questions = []
        # İstenen sayıya ulaşana kadar yerel soruları listeye ekle
        while len(questions) < total_count and filtered:
            item = random.choice(filtered).copy()
            item["id"] = random.randint(1000, 9999)
            questions.append(item)

    return jsonify({"questions": questions})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
