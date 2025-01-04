import pytest
from app import app

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_index(client):
    res = client.get('/')
    assert res.status_code == 200

def test_create_wallet(client):
    res = client.post('/api/create_wallet')
    json_data = res.get_json()
    assert 'success' in json_data