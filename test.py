import os
import sys
from google import genai

try:
    print("Test basliyor...")
    # Anahtar koda gömülmez; GEMINI_API_KEY ortam değişkeninden okunur.
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents='Merhaba, bu bir test mesajidir.'
    )
    print("BASARILI! Cevap:", response.text)
except Exception as e:
    print("BASARISIZ:", str(e))
    sys.exit(1)
