import os
import sys
import json
import time
from typing import List, Dict, Any, Optional

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from hermes_sentinel import Sentinel

# Hermes Sentinel Crash Telemetrisi
Sentinel.init(app_id="otomatik-sinav-asistani", version="2.0.0", endpoint="http://localhost:8765/api/telemetry")

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

API_KEY = os.environ.get("GEMINI_API_KEY")

# Eğer .env dosyası varsa oku
if not API_KEY and os.path.exists(".env"):
    try:
        with open(".env", "r", encoding="utf-8") as env_f:
            for line in env_f:
                line = line.strip()
                if line.startswith("GEMINI_API_KEY="):
                    API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    except Exception:
        pass

client = None
if API_KEY:
    try:
        from google import genai
        client = genai.Client(api_key=API_KEY)
    except Exception as e:
        print(f"GenAI Client baslatilamadi: {e}")

PDF_FILES = [
    "sosyalbilgiler5-1.unit.pdf", 
    "sosyalbilgiler5-2.unit.pdf",
    "sosyalbilgiler5-3.unit.pdf",
    "sosyalbilgiler5-4.unit.pdf",
    "sosyalbilgiler5-5.unit.pdf",
    "sosyalbilgiler5-6.unit.pdf"
]
uploaded_files = []

def setup_gemini_files():
    if not client:
        print("[!] Gemini API anahtari tanimli degil, sistem Mock/Lokal modda calisacak.")
        return

    try:
        print("Mevcut Gemini dosyalari kontrol ediliyor...")
        existing_files = list(client.files.list())
        
        existing_names = {}
        for f in existing_files:
            if hasattr(f, 'display_name') and f.display_name:
                existing_names[f.display_name] = f
            
        for pdf_name in PDF_FILES:
            if pdf_name in existing_names:
                print(f"[*] {pdf_name} zaten yuklu. ID: {existing_names[pdf_name].name}")
                uploaded_files.append(existing_names[pdf_name])
            else:
                if os.path.exists(pdf_name):
                    print(f"[!] {pdf_name} sisteme yukleniyor...")
                    uploaded_file = client.files.upload(file=pdf_name, config={'display_name': pdf_name})
                    
                    while True:
                        f = client.files.get(name=uploaded_file.name)
                        state = str(getattr(f, 'state', 'PROCESSING'))
                        if 'PROCESSING' in state:
                            time.sleep(3)
                        else:
                            break
                            
                    print(f"[*] {pdf_name} kullanima hazir!")
                    uploaded_files.append(uploaded_file)
                else:
                    print(f"HATA: {pdf_name} klasorde bulunamadi!")
    except Exception as e:
        print(f"Gemini dosya senkronizasyonu atlandi: {e}")

# Web Arayüzü Rotaları
@app.route('/')
def index():
    if os.path.exists("teacher.html"):
        return send_from_directory(".", "teacher.html")
    elif os.path.exists("index.html"):
        return send_from_directory(".", "index.html")
    return jsonify({"status": "ok", "app": "EduAI Sınav Asistanı API"})

@app.route('/<path:path>')
def static_files(path):
    if os.path.exists(path):
        return send_from_directory(".", path)
    return jsonify({"error": "Dosya bulunamadi"}), 404

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "app_id": "otomatik-sinav-asistani",
        "version": "2.0.0",
        "has_api_key": bool(API_KEY),
        "pdf_files_count": len([p for p in PDF_FILES if os.path.exists(p)])
    })

def generate_mock_questions(grade: str, subject: str, unit: str, count: int) -> List[Dict[str, Any]]:
    """API anahtarı veya internet olmadığında çalışan güvenli MEB müfredat soru üreteci."""
    unit_samples = [
        {
            "soru": f"5. Sınıf {subject} dersi kapsamında, bireylerin içinde yaşadıkları toplumdaki hak ve sorumluluklarını bilmeleri neden önemlidir?",
            "secenekler": [
                "A) Toplumsal barış ve uyumu güçlendirmek için",
                "B) Yalnızca bireysel çıkarlarını korumak için",
                "C) Kurallara uymaktan kaçınmak için",
                "D) Ders notlarını yükseltmek için"
            ],
            "dogru_cevap": "A"
        },
        {
            "soru": "Aşağıdakilerden hangisi bir çocuğun okulda sahip olduğu temel haklardan biridir?",
            "secenekler": [
                "A) Güvenli ve sağlıklı bir ortamda eğitim alma hakkı",
                "B) Okul kurallarını tek başına belirleme hakkı",
                "C) İstediği zaman ders saatlerini değiştirme hakkı",
                "D) Sadece oyun saatlerine katılma hakkı"
            ],
            "dogru_cevap": "A"
        },
        {
            "soru": "Ortak mirasımız olan tarihi eserleri ve doğal varlıkları korumak kimin görevidir?",
            "secenekler": [
                "A) Yalnızca turistlerin",
                "B) Tüm vatandaşların ve insanlığın",
                "C) Yalnızca arkeologların",
                "D) Sadece belediye temizlik görevlilerinin"
            ],
            "dogru_cevap": "B"
        },
        {
            "soru": "Demokrasinin temel ilkelerinden olan 'milli egemenlik' ne anlama gelir?",
            "secenekler": [
                "A) Yönetme yetkisinin millete ait olması",
                "B) Kararların tek bir kişi tarafından alınması",
                "C) Kanunların kişiye özel çıkarılması",
                "D) Seçimlerin yapılmaması"
            ],
            "dogru_cevap": "A"
        },
        {
            "soru": "Bilinçli bir tüketicinin alışveriş yaparken dikkat etmesi gereken en önemli husus hangisidir?",
            "secenekler": [
                "A) Ürünün son kullanma tarihi ve garanti belgesini kontrol etmek",
                "B) Yalnızca en pahalı markayı tercih etmek",
                "C) Reklamlarda en çok görünen ürünü almak",
                "D) Fiş veya fatura almaktan kaçınmak"
            ],
            "dogru_cevap": "A"
        }
    ]
    return unit_samples[:max(1, min(count, len(unit_samples)))]

@app.route('/generate', methods=['POST', 'OPTIONS'])
def generate_questions():
    print("--- YENI ISTEK GELDI ---")
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    try:
        data = request.json or {}
        grade = data.get('grade', '5')
        subject = data.get('subject', 'Sosyal Bilgiler')
        unit = data.get('unit', '')
        count = data.get('count', 5)
        
        prompt = f"""
Sen bir {grade}. sinif {subject} ogretmenisin. 
Yalnizca sana dosya olarak sagladigim MEB kitaplarindaki bilgileri kullanarak {unit} unitesi ile alakali {count} adet coktan secmeli (A, B, C, D sikli) soru hazirla.
Kesinlikle kendi on bilginle disaridan bilgi ekleme. Metnin disina cikma.
Cevabini asagidaki JSON formatinda don. Dizi (Array) formatinda olmali:

[
  {{
    "soru": "Soru metni",
    "secenekler": ["A) Ilk secenek", "B) Ikinci secenek", "C) Ucuncu secenek", "D) Dorduncu secenek"],
    "dogru_cevap": "B"
  }}
]

Sadece ve sadece gecerli JSON cevir, baska hicbir aciklama veya markdown karakteri (```json vb.) kullanma.
"""
        print(f"Istek alindi: {grade}. Sinif {subject} - {unit} - {count} Soru")
        
        # Hangi ünite seçildiyse o ünitenin PDF dosyasını bul (Örn: "1. Ünite..." -> 1)
        unit_number = ''.join([c for c in str(unit).split('.')[0] if c.isdigit()])
        if not unit_number:
            unit_number = "1"
            
        target_filename = f"sosyalbilgiler5-{unit_number}.unit.pdf"
        
        selected_file = None
        for f in uploaded_files:
            if hasattr(f, 'display_name') and f.display_name == target_filename:
                selected_file = f
                break
                
        # Eger bulunamazsa (veya eski API kullaniliyorsa) isim icinde arama yap
        if not selected_file:
            for f in uploaded_files:
                if target_filename in getattr(f, 'display_name', '') or target_filename in getattr(f, 'name', ''):
                    selected_file = f
                    break

        if not selected_file and len(uploaded_files) > 0:
            selected_file = uploaded_files[0]
            
        file_to_pass = [selected_file] if selected_file else []

        if not client:
            # API anahtarı yoksa doğrudan MEB müfredatı mock sorularını döndür
            print("[*] Mock modda soru üretiliyor...")
            questions = generate_mock_questions(grade, subject, unit, count)
            return jsonify({"success": True, "questions": questions, "source": "mock_curriculum"})

        max_retries = 3
        retry_delay = 2
        response = None
        
        for attempt in range(max_retries):
            try:
                print(f"Deneme {attempt + 1}/{max_retries}... (Kullanilan Dosya: {getattr(selected_file, 'display_name', 'Bilinmiyor')})")
                # Stabil Flash modelleri dene
                model_name = 'gemini-2.5-flash'
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[*file_to_pass, prompt]
                    )
                except Exception:
                    response = client.models.generate_content(
                        model='gemini-1.5-flash',
                        contents=[*file_to_pass, prompt]
                    )
                break
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    print(f"Tekrar deneniyor ({attempt+1})...")
                    time.sleep(retry_delay)
                else:
                    print(f"[!] Gemini hatasi, guvenli yedek MEB sorularina geciliyor: {e}")
                    questions = generate_mock_questions(grade, subject, unit, count)
                    return jsonify({"success": True, "questions": questions, "source": "fallback_curriculum"})
        
        if response and hasattr(response, 'text') and response.text:
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            try:
                questions = json.loads(text)
                return jsonify({"success": True, "questions": questions, "source": "gemini_ai"})
            except Exception:
                pass

        questions = generate_mock_questions(grade, subject, unit, count)
        return jsonify({"success": True, "questions": questions, "source": "fallback_curriculum"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            sentinel = Sentinel.get()
            if sentinel:
                sentinel.report_crash(e, {"route": "/generate"})
        except Exception:
            pass
        return jsonify({"success": False, "error": str(e), "trace": traceback.format_exc()}), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("Yapay Zeka Sunucusu Calisiyor!")
    print("Sistem hazir! Arayuzden istek gonderebilirsiniz.")
    print("="*50 + "\n")
    # Production (Canlı) ortam ayarları: 
    # host='0.0.0.0' dışarıdan erişime izin verir
    # debug=False güvenlik açığı oluşturmaması için zorunludur.
    app.run(host='0.0.0.0', port=5000, debug=False)
