import os
import json
import time
import traceback
from typing import List, Dict, Any

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from hermes_sentinel import Sentinel

# Hermes Sentinel Crash Telemetrisi
Sentinel.init(app_id="otomatik-sinav-asistani", version="2.0.0", endpoint="http://localhost:8765/api/telemetry")

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

# API anahtarı YALNIZCA ortam değişkeninden ya da .env dosyasından okunur. Kaynak koda gömülmez.
API_KEY = os.environ.get("GEMINI_API_KEY")
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

# Kullanılacak model; ortam değişkeni ile değiştirilebilir. Sırayla denenir.
GEMINI_MODELS = [m for m in [os.environ.get("GEMINI_MODEL"), "gemini-2.5-flash", "gemini-1.5-flash"] if m]

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
    "sosyalbilgiler5-6.unit.pdf",
]
uploaded_files = []


def setup_gemini_files():
    """Ünite PDF'lerini Gemini Files API'ye yükler (zaten yüklü olanları yeniden yüklemez)."""
    if not client:
        print("[!] Gemini API anahtari tanimli degil, sistem Mock/Lokal modda calisacak.")
        return
    try:
        existing_names = {}
        for f in client.files.list():
            if getattr(f, "display_name", None):
                existing_names[f.display_name] = f

        for pdf_name in PDF_FILES:
            if pdf_name in existing_names:
                print(f"[*] {pdf_name} zaten yuklu. ID: {existing_names[pdf_name].name}")
                uploaded_files.append(existing_names[pdf_name])
                continue
            if not os.path.exists(pdf_name):
                print(f"HATA: {pdf_name} klasorde bulunamadi!")
                continue
            print(f"[!] {pdf_name} sisteme yukleniyor...")
            uploaded_file = client.files.upload(file=pdf_name, config={"display_name": pdf_name})
            while "PROCESSING" in str(getattr(client.files.get(name=uploaded_file.name), "state", "PROCESSING")):
                time.sleep(3)
            print(f"[*] {pdf_name} kullanima hazir!")
            uploaded_files.append(uploaded_file)
    except Exception as e:
        print(f"Gemini dosya senkronizasyonu atlandi: {e}")


# Sunucu baslarken PDF'leri hazirla (client yoksa fonksiyon kendi kendine çıkar)
setup_gemini_files()


# Web Arayüzü Rotaları
@app.route("/")
def index():
    if os.path.exists("teacher.html"):
        return send_from_directory(".", "teacher.html")
    if os.path.exists("index.html"):
        return send_from_directory(".", "index.html")
    return jsonify({"status": "ok", "app": "EduAI Sınav Asistanı API"})


@app.route("/<path:path>")
def static_files(path):
    if os.path.isfile(path):
        return send_from_directory(".", path)
    return jsonify({"error": "Dosya bulunamadi"}), 404


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "app_id": "otomatik-sinav-asistani",
        "version": "2.0.0",
        "has_api_key": bool(API_KEY),
        "pdf_files_count": len([p for p in PDF_FILES if os.path.exists(p)]),
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
                "D) Ders notlarını yükseltmek için",
            ],
            "dogru_cevap": "A",
        },
        {
            "soru": "Aşağıdakilerden hangisi bir çocuğun okulda sahip olduğu temel haklardan biridir?",
            "secenekler": [
                "A) Güvenli ve sağlıklı bir ortamda eğitim alma hakkı",
                "B) Okul kurallarını tek başına belirleme hakkı",
                "C) İstediği zaman ders saatlerini değiştirme hakkı",
                "D) Sadece oyun saatlerine katılma hakkı",
            ],
            "dogru_cevap": "A",
        },
        {
            "soru": "Ortak mirasımız olan tarihi eserleri ve doğal varlıkları korumak kimin görevidir?",
            "secenekler": [
                "A) Yalnızca turistlerin",
                "B) Tüm vatandaşların ve insanlığın",
                "C) Yalnızca arkeologların",
                "D) Sadece belediye temizlik görevlilerinin",
            ],
            "dogru_cevap": "B",
        },
        {
            "soru": "Demokrasinin temel ilkelerinden olan 'milli egemenlik' ne anlama gelir?",
            "secenekler": [
                "A) Yönetme yetkisinin millete ait olması",
                "B) Kararların tek bir kişi tarafından alınması",
                "C) Kanunların kişiye özel çıkarılması",
                "D) Seçimlerin yapılmaması",
            ],
            "dogru_cevap": "A",
        },
        {
            "soru": "Bilinçli bir tüketicinin alışveriş yaparken dikkat etmesi gereken en önemli husus hangisidir?",
            "secenekler": [
                "A) Ürünün son kullanma tarihi ve garanti belgesini kontrol etmek",
                "B) Yalnızca en pahalı markayı tercih etmek",
                "C) Reklamlarda en çok görünen ürünü almak",
                "D) Fiş veya fatura almaktan kaçınmak",
            ],
            "dogru_cevap": "A",
        },
    ]
    return unit_samples[: max(1, min(int(count), len(unit_samples)))]


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _select_pdf(unit: str):
    """'1. Ünite ...' gibi bir ünite metninden ilgili PDF'i seçer; bulunamazsa ilk dosyayı döndürür."""
    digits = "".join(c for c in str(unit).split(".")[0] if c.isdigit()) or "1"
    target = f"sosyalbilgiler5-{digits}.unit.pdf"
    for f in uploaded_files:
        if getattr(f, "display_name", "") == target:
            return f
    for f in uploaded_files:
        if target in (getattr(f, "display_name", "") or "") or target in (getattr(f, "name", "") or ""):
            return f
    return uploaded_files[0] if uploaded_files else None


@app.route("/generate", methods=["POST", "OPTIONS"])
def generate_questions():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    try:
        data = request.get_json(silent=True) or {}
        grade = data.get("grade", "5")
        subject = data.get("subject", "Sosyal Bilgiler")
        unit = data.get("unit", "")
        count = int(data.get("count", 5))
        print(f"Istek alindi: {grade}. Sinif {subject} - {unit} - {count} Soru")

        # API anahtarı yoksa doğrudan MEB müfredatı mock sorularını döndür
        if not client:
            questions = generate_mock_questions(grade, subject, unit, count)
            return jsonify({"success": True, "questions": questions, "source": "mock_curriculum"})

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
        selected_file = _select_pdf(unit)
        contents = [*([selected_file] if selected_file else []), prompt]

        response = None
        last_error = None
        for model_name in GEMINI_MODELS:
            for attempt in range(3):
                try:
                    response = client.models.generate_content(model=model_name, contents=contents)
                    break
                except Exception as e:
                    last_error = e
                    if attempt < 2:
                        time.sleep(2 * (attempt + 1))
            if response is not None:
                break

        if response is None or not getattr(response, "text", None):
            print(f"[!] Gemini hatasi, guvenli yedek MEB sorularina geciliyor: {last_error}")
            questions = generate_mock_questions(grade, subject, unit, count)
            return jsonify({"success": True, "questions": questions, "source": "fallback_curriculum"})

        questions = json.loads(_strip_code_fence(response.text))
        return jsonify({"success": True, "questions": questions, "source": "gemini_ai"})

    except Exception as e:
        traceback.print_exc()
        try:
            sentinel = Sentinel.get()
            if sentinel:
                sentinel.report_crash(e, {"route": "/generate"})
        except Exception:
            pass
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("=" * 50)
    print("Yapay Zeka Sunucusu Calisiyor!")
    print("Sistem hazir! Arayuzden istek gonderebilirsiniz.")
    print("=" * 50)
    # host='0.0.0.0' dışarıdan erişime izin verir; debug=False zorunlu (debugger uzaktan çalıştırılabilir).
    app.run(host="0.0.0.0", port=5000, debug=False)
