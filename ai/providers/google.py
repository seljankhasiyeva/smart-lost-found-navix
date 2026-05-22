"""Google Gemini provider adapters via direct REST API."""
from __future__ import annotations
import base64
import json
import os
from pathlib import Path
import numpy as np
import requests
from ai.providers.base import VLMProvider, EmbeddingProvider, ProviderError

BASE = "https://generativelanguage.googleapis.com/v1"


class GeminiVLM(VLMProvider):
    def __init__(self, model=None, *, api_key=None):
        self.model = model or os.getenv("LLM_MODEL", "gemini-2.0-flash")
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self._api_key:
            raise ProviderError("GOOGLE_API_KEY is not set.")

    def describe(self, image_path, prompt, *, json_schema=None):
        path = Path(image_path)
        if not path.is_file():
            raise FileNotFoundError(image_path)
        full_prompt = prompt
        if json_schema is not None:
            full_prompt = prompt + "\n\nReturn ONLY valid JSON:\n" + json.dumps(json_schema, indent=2)
        import mimetypes
        mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
        b64 = base64.b64encode(path.read_bytes()).decode()
        url = f"{BASE}/models/{self.model}:generateContent?key={self._api_key}"
        body = {"contents": [{"parts": [
            {"inlineData": {"mimeType": mime, "data": b64}},
            {"text": full_prompt}
        ]}]}
        try:
            r = requests.post(url, json=body, timeout=60)
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            raise ProviderError(f"Gemini VLM call failed: {e}") from e


class GeminiEmbedding(EmbeddingProvider):
    def __init__(self, model=None, *, api_key=None):
        self.model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-004")
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self._api_key:
            raise ProviderError("GOOGLE_API_KEY is not set.")
        self._dim = 768

    @property
    def dimension(self):
        return self._dim

    def embed(self, text):
        if not text.strip():
            raise ValueError("Cannot embed empty string.")
        url = f"{BASE}/models/{self.model}:embedContent?key={self._api_key}"
        body = {"content": {"parts": [{"text": text}]}}
        try:
            r = requests.post(url, json=body, timeout=30)
            r.raise_for_status()
            vec = np.asarray(r.json()["embedding"]["values"], dtype=np.float32)
        except Exception as e:
            raise ProviderError(f"Gemini embedding call failed: {e}") from e
        norm = float(np.linalg.norm(vec))
        if norm == 0.0:
            raise ProviderError("Provider returned a zero vector.")
        return vec / norm