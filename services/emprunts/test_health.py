"""
Tests unitaires pour le service Emprunts
"""
import pytest
from app import app


@pytest.fixture
def client():
    """Crée un client Flask pour les tests"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_emprunts_health(client):
    """Test du endpoint /health"""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['service'] == 'emprunts'
    assert response.json['status'] == 'ok'
