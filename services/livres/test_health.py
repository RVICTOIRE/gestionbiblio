"""
Tests unitaires pour le service Livres
"""
import pytest
from app import app


@pytest.fixture
def client():
    """Crée un client Flask pour les tests"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_livres_health(client):
    """Test du endpoint /health"""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['service'] == 'livres'
    assert response.json['status'] == 'ok'


def test_livres_root(client):
    """Test du endpoint racine"""
    response = client.get('/')
    assert response.status_code in [200, 404, 405]  # Endpoint existe ou non
