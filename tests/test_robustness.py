import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.api import app
from src.config import settings
from src.core.exceptions import ItemNotFound

client = TestClient(app)

def test_register_lost_file_too_large():
    large_data = b"0" * (settings.max_image_size_mb * 1024 * 1024 + 1024)
    
    jpeg_header = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"
    payload = jpeg_header + large_data

    response = client.post(
        "/items/lost",
        files={"image": ("test.jpg", payload, "image/jpeg")},
        data={"text": "Lost keys near the park"}
    )
    
    assert response.status_code == 400
    assert "File size exceeds the maximum allowed limit" in response.json()["detail"]


def test_register_found_invalid_file_type():
    invalid_payload = b"import os; os.system('rm -rf /')"
    
    response = client.post(
        "/items/found",
        files={"image": ("attack.py", invalid_payload, "text/x-python")},
        data={"text": "Found a suspicious bag"}
    )
    
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_get_matches_invalid_or_missing_uuid():
    response = client.get("/items/invalid-uuid-123/matches")
    assert response.status_code == 400
    
    with patch("src.concurrency.pipeline.find_matches", new_callable=AsyncMock) as mock_find:
        mock_find.side_effect = ItemNotFound("Item not found")
        
        random_uuid = "11111111-2222-3333-4444-555555555555"
        response = client.get(f"/items/{random_uuid}/matches")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@patch("src.concurrency.pipeline.describe_item", new_callable=AsyncMock)
@patch("src.concurrency.pipeline.get_embedding", new_callable=AsyncMock)
def test_successful_registration_with_ai_mock(mock_embed, mock_vlm):
    mock_vlm.return_value = {"description": "A shiny silver key", "confidence": 0.95}
    mock_embed.return_value = [0.1, 0.2, 0.3] 
    
    valid_image = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"0" * 100
    
    with patch("src.storage.repository.ItemRepository.create", new_callable=AsyncMock) as mock_create, \
         patch("src.storage.repository.ItemRepository.update_ai_fields", new_callable=AsyncMock) as mock_update:
        
        mock_create.return_value = None
        mock_update.return_value = None

        response = client.post(
            "/items/lost",
            files={"image": ("keys.jpg", valid_image, "image/jpeg")},
            data={"text": "Silver keys"}
        )
        
        assert response.status_code == 200
        assert "item_id" in response.json()
        
        mock_vlm.assert_called_once()
        mock_embed.assert_called_once()