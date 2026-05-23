# tests/test_services.py

from unittest.mock import patch

import pytest

from src.services import ai_service


@pytest.mark.asyncio
async def test_embed_cache_hit():
    """
    If get_embedding() is called twice with the same text,
    the second result must come from cache.

    Expected:
    - First call uses embed_module.embed()
    - Second call uses _embed_cache
    - embed_module.embed() is called only once
    """

    ai_service._embed_cache.clear()

    with patch(
        "src.services.ai_service.embed_module.embed",
        return_value=[0.1] * 1536,
    ) as mock_embed:
        first_result = await ai_service.get_embedding("black wallet")
        second_result = await ai_service.get_embedding("black wallet")

    assert first_result == [0.1] * 1536
    assert second_result == [0.1] * 1536
    assert mock_embed.call_count == 1


@pytest.mark.asyncio
async def test_embed_cache_miss():
    """
    If get_embedding() is called with different text values,
    each different text should trigger a separate embedding call.

    Expected:
    - "red bag" calls embed_module.embed()
    - "blue jacket" calls embed_module.embed()
    - total call count is 2
    """

    ai_service._embed_cache.clear()

    with patch(
        "src.services.ai_service.embed_module.embed",
        return_value=[0.2] * 1536,
    ) as mock_embed:
        first_result = await ai_service.get_embedding("red bag")
        second_result = await ai_service.get_embedding("blue jacket")

    assert first_result == [0.2] * 1536
    assert second_result == [0.2] * 1536
    assert mock_embed.call_count == 2


@pytest.mark.asyncio
async def test_embed_cache_stores_text_key():
    """
    After get_embedding() is called, the text should exist
    as a key inside _embed_cache.
    """

    ai_service._embed_cache.clear()

    with patch(
        "src.services.ai_service.embed_module.embed",
        return_value=[0.3] * 1536,
    ):
        result = await ai_service.get_embedding("green backpack")

    assert "green backpack" in ai_service._embed_cache
    assert ai_service._embed_cache["green backpack"] == result


@pytest.mark.asyncio
async def test_describe_item_returns_dict():
    """
    describe_item() should return a dictionary.

    If the provided ai.vlm.describe_item() returns a dict,
    ai_service.describe_item() should pass it through correctly.
    """

    fake_description = {
        "object_class": "wallet",
        "colours": ["black"],
        "brand": "unknown",
        "marks": "small scratch",
        "confidence": 0.9,
    }

    with patch(
        "src.services.ai_service.vlm_module.describe_item",
        return_value=fake_description,
    ) as mock_describe:
        result = await ai_service.describe_item(
            image_path="/tmp/wallet.jpg",
            user_text="black wallet",
        )

    assert result == fake_description
    assert isinstance(result, dict)
    assert result["object_class"] == "wallet"
    assert result["confidence"] == 0.9
    assert mock_describe.call_count == 1


@pytest.mark.asyncio
async def test_describe_item_converts_pydantic_like_object_to_dict():
    """
    Some AI providers may return a Pydantic-like object instead of a plain dict.
    ai_service.describe_item() should convert it using model_dump().
    """

    class FakeVLMResult:
        def model_dump(self):
            return {
                "object_class": "phone",
                "colours": ["white"],
                "brand": "unknown",
                "marks": "",
                "confidence": 0.85,
            }

    with patch(
        "src.services.ai_service.vlm_module.describe_item",
        return_value=FakeVLMResult(),
    ):
        result = await ai_service.describe_item(
            image_path="/tmp/phone.jpg",
            user_text="white phone",
        )

    assert isinstance(result, dict)
    assert result["object_class"] == "phone"
    assert result["confidence"] == 0.85


def test_top_matches_delegates_to_similarity_module():
    """
    top_matches() should delegate the actual similarity ranking
    to the provided ai.similarity.top_k() function.
    """

    query_vec = [0.1, 0.2, 0.3]
    candidates = [
        [0.1, 0.2, 0.3],
        [0.9, 0.8, 0.7],
    ]

    fake_results = [(0, 0.99), (1, 0.55)]

    with patch(
        "src.services.ai_service.sim_module.top_k",
        return_value=fake_results,
    ) as mock_top_k:
        result = ai_service.top_matches(query_vec, candidates, k=2)