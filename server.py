import os
import sys
import json
import time

# Windows arka plan process'lerinde (daemon) print() komutunun OSError fırlatmasını önlemek için log dosyasına yönlendir.
sys.stdout = open("server.log", "a", encoding="utf-8")
sys.stderr = sys.stdout

from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai

app = Flask(__name__)
CORS(app)

API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    # Eger çevre değişkenlerinde yoksa (lokal test için) varsayılanı kullan
    API_KEY = "AQ.Ab8RN6K6IkjXeML9waU1bjtiTyaU0hnY1Aek7mwqcKn2r9xr0g"

client = genai.Client(api_key=API_KEY)

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
    print("Mevcut Gemini dosyalari kontrol ediliyor...")
    existing_files = list(client.files.list())
    
    # Yeni SDK'da 'display_name' ve 'name' property'leri var
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
                print(f"[!] {pdf_name} sisteme yukleniyor (100MB oldugu icin biraz surebilir)...")
                uploaded_file = client.files.upload(file=pdf_name, config={'display_name': pdf_name})
                print(f"[*] Yuklendi: {uploaded_file.name}. Yapay zeka tarafindan islenmesi bekleniyor...")
                
                # Dosyanin islenmesini bekle
                while True:
                    f = client.files.get(name=uploaded_file.name)
                    # State genellikle string dondurur, ACTIVE veya PROCESSING
                    state = str(getattr(f, 'state', 'PROCESSING'))
                    if 'PROCESSING' in state:
                        print(".", end="", flush=True)
                        time.sleep(5)
                    else:
                        break
                        
                print(f"\n[*] {pdf_name} isleme tamamlandi ve kullanima hazir!")
                uploaded_files.append(uploaded_file)
            else:
                print(f"HATA: {pdf_name} klasorde bulunamadi!")

# Sunucu baslarken PDF'leri hazirla
setup_gemini_files()

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

        max_retries = 5
        retry_delay = 5
        response = None
        
        for attempt in range(max_retries):
            try:
                print(f"Deneme {attempt + 1}/{max_retries}... (Kullanilan Dosya: {getattr(selected_file, 'display_name', 'Bilinmiyor')})")
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=[*file_to_pass, prompt]
                )
                break # Basarili olursa donguden cik
            except Exception as e:
                error_msg = str(e)
                if "503" in error_msg or "UNAVAILABLE" in error_msg:
                    if attempt < max_retries - 1:
                        print(f"Sunucu yogun, {retry_delay} saniye sonra tekrar deneniyor...")
                        time.sleep(retry_delay)
                    else:
                        raise Exception("Google sunuculari su an asiri yogun. Lutfen 5-10 dakika sonra tekrar deneyin.")
                else:
                    raise e # Baska bir hataysa direkt firlat
        
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        questions = json.loads(text)
        return jsonify({"success": True, "questions": questions})
    except Exception as e:
        import traceback
        traceback.print_exc()
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
