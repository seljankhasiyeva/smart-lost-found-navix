"""Google Gemini provider adapters using official google-genai SDK."""

from __future__ import annotations
import os
from pathlib import Path
import numpy as np
from google import genai
from google.genai import types
from ai.providers.base import VLMProvider, EmbeddingProvider, ProviderError

class GeminiVLM(VLMProvider):
    def __init__(self, model: str | None = None, *, api_key: str | None = None) -> None:
        self.model = model or os.getenv('LLM_MODEL') or os.getenv('GEMINI_VLM_MODEL') or 'gemini-2.5-flash'
        api_key = api_key or os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY') or os.getenv('LLM_API_KEY')
        if not api_key:
            raise ProviderError('GOOGLE_API_KEY is not set.')
        self.client = genai.Client(api_key=api_key)

    def describe(self, image_path: str, prompt: str, *, json_schema: dict | None = None) -> str:
        path = Path(image_path)
        if not path.is_file():
            raise FileNotFoundError(image_path)
        
        try:
            with open(path, 'rb') as f:
                image_bytes = f.read()
                
            config = types.GenerateContentConfig()
            if json_schema is not None:
                config.response_mime_type = "application/json"
                config.response_schema = json_schema

            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png")
                ],
                config=config
            )
            return response.text.strip()
        except Exception as e:
            raise ProviderError(f'Gemini VLM call failed: {e}')

class GeminiEmbedding(EmbeddingProvider):
    def __init__(self, model: str | None = None, *, api_key: str | None = None) -> None:
        self.model = 'text-embedding-004'
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY') or os.getenv('EMBEDDING_API_KEY')
        if not self.api_key:
            raise ProviderError('GOOGLE_API_KEY is not set.')
        
        # 404 xətasını həll edən əsas hissə: API versiyasını v1beta-ya məcbur edirik
        self.client = genai.Client(api_key=self.api_key, http_options={'api_version': 'v1beta'})
        self._dim = 768

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, text: str) -> np.ndarray:
        if not text.strip():
            raise ValueError('Cannot embed empty string.')
        try:
            response = self.client.models.embed_content(
                model=self.model,
                contents=text
            )
            val = response.embeddings[0].values
            vec = np.asarray(val, dtype=np.float32)
            norm = float(np.linalg.norm(vec))
            if norm == 0.0:
                raise ProviderError('Provider returned a zero vector.')
            return vec / norm
        except Exception as e:
            raise ProviderError(f'Gemini embedding call failed: {e}')
