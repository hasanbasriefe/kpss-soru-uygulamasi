import os
import json
import random
from flask import Flask, render_template, request, jsonify

# app.py dosyasının bulunduğu tam klasör yolunu garantiye alıyoruz
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
    print(f"Uyarı: {JSON_PATH} dosya konumunda questions.json bulunamadı!")
    return []

app = Flask(__name__)

# Yerel havuzu yükle
def load_local_questions():
    if os.path.exists("questions.json"):
        with open("questions.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# Yapay zeka ile dinamik soru üreten fonksiyon (İhtiyaç halinde tetiklenir)
def generate_ai_question(ders):
    """
    Yerel sorular bittiğinde Gemini API çağrısı ile KPSS formatında
    dinamik soru üreten şablon fonksiyon.
    """
    # API Entegrasyonu örneği:
    # prompt = f"KPSS Ortaöğretim seviyesinde {ders} dersinden 5 şıklı, tek doğru cevaplı ve çözümlü bir soru üret."
    # Dönen cevabı JSON formatında ayrıştırıp listeye ekler.
    return {
        "id": random.randint(1000, 9999),
        "ders": ders,
        "soru": f"[{ders} - Dinamik Soru] Aşağıdakilerden hangisi bu dersin temel ilkelerindendir?",
        "secenekler": ["A) Tanım 1", "B) Tanım 2", "C) Tanım 3", "D) Tanım 4", "E) Tanım 5"],
        "dogruCevap": "A",
        "cozum": "Bu soru dinamik motor tarafından üretilmiştir. Temel kurallar gereği doğru yanıt A şıkkıdır."
    }

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/get-test", methods=["POST"])
def get_test():
    data = request.json or {}
    selected_dersler = data.get("dersler", [])
    total_count = int(data.get("soruSayisi", 10))

    pool = load_local_questions()
    filtered = [q for q in pool if q["ders"] in selected_dersler]
    random.shuffle(filtered)

    selected_questions = []

    # 1. Aşama: Yerel havuzdan soruları al
    if len(filtered) >= total_count:
        selected_questions = filtered[:total_count]
    else:
        selected_questions = list(filtered)
        eksik = total_count - len(selected_questions)
        
        # 2. Aşama: Havuz yetersizse dinamik soru üret (Karma Model)
        for _ in range(eksik):
            hedef_ders = random.choice(selected_dersler) if selected_dersler else "Güncel Bilgiler"
            dynamic_q = generate_ai_question(hedef_ders)
            selected_questions.append(dynamic_q)

    random.shuffle(selected_questions)
    return jsonify({"questions": selected_questions})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)