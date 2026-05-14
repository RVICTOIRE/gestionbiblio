"""
Tests unitaires pour le service Recommandation
"""
import pytest
from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def test_recommandation_health():
    """Test du endpoint /health"""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['service'] == 'recommandation'
    assert response.json['status'] == 'ok'


def test_recommandation_root():
    """Test du endpoint racine"""
    response = client.get('/')
    assert response.status_code in [200, 404]
