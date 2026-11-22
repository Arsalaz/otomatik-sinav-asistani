"""Otomatik Sınav Asistanı v2.0 - Test Paketi
"""
import pytest
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from server import app, generate_mock_questions
from hermes_sentinel import Sentinel


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_01_sentinel_initialization():
    """Hermes Sentinel'in başarıyla yapılandırıldığını doğrular."""
    inst = Sentinel.get()
    assert inst is not None
    assert inst.app_id in ("otomatik-sinav-asistani", "unknown")


def test_02_health_endpoint(client):
    """Health check endpoint'inin doğru yanıt verdiğini test eder."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["app_id"] == "otomatik-sinav-asistani"
    assert "pdf_files_count" in data


def test_03_static_routing(client):
    """Ana sayfa ve statik dosyaların servis edildiğini test eder."""
    res = client.get("/")
    assert res.status_code in (200, 302)

    res_css = client.get("/styles.css")
    assert res_css.status_code == 200
    assert "60-30-10" in res_css.get_data(as_text=True)


def test_04_mock_question_generator():
    """Müfredat soru üretecinin A, B, C, D şıklı geçerli şema ürettiğini test eder."""
    questions = generate_mock_questions("5", "Sosyal Bilgiler", "1", 3)
    assert isinstance(questions, list)
    assert len(questions) == 3
    for q in questions:
        assert "soru" in q
        assert "secenekler" in q
        assert len(q["secenekler"]) == 4
        assert "dogru_cevap" in q
        assert q["dogru_cevap"] in ["A", "B", "C", "D"]


def test_05_generate_endpoint_mock(client):
    """POST /generate uç noktasının geçerli JSON döndürdüğünü test eder."""
    payload = {
        "grade": "5",
        "subject": "Sosyal Bilgiler",
        "unit": "1",
        "count": 2
    }
    res = client.post("/generate", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "questions" in data
    assert len(data["questions"]) > 0


def test_06_pdf_files_exist():
    """MEB 5. sınıf Sosyal Bilgiler ünite PDF'lerinin varlığını doğrular."""
    pdf_list = [f"sosyalbilgiler5-{i}.unit.pdf" for i in range(1, 7)]
    for p in pdf_list:
        p_path = os.path.join(os.path.dirname(__file__), p)
        assert os.path.exists(p_path), f"Eksik PDF dosyası: {p}"
        assert os.path.getsize(p_path) > 1000000, f"Bozuk veya çok küçük PDF: {p}"
