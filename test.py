from google import genai
import sys

try:
    print("Test basliyor...")
    client = genai.Client(api_key="AQ.Ab8RN6K6IkjXeML9waU1bjtiTyaU0hnY1Aek7mwqcKn2r9xr0g")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents='Merhaba, bu bir test mesajidir.'
    )
    print("BASARILI! Cevap:", response.text)
except Exception as e:
    print("BASARISIZ:", str(e))
    sys.exit(1)
