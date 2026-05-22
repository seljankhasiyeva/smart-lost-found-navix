"""Google Gemini provider adapters using the official google-genai SDK."""

from __future__ import annotations
import os
from pathlib import Path
import numpy as np
from google import genai
from google.genai import types
from ai.providers.base import VLMProvider, EmbeddingProvider, ProviderError

def sanitize_json_schema(schema: dict) -> dict:
    """Sanitizes legacy JSON-Schema definitions to make them compatible with the new Google GenAI SDK.
    
    This function removes forbidden attributes like 'additionalProperties' and flattens
    type definitions that contain multiple types (e.g., ['string', 'null']) into a single,
    primitive string type. This prevents internal SDK crashes such as AttributeError and 
    Pydantic validation schema mismatches.
    """
    if not isinstance(schema, dict):
        return schema

    # 1. Strip 'additionalProperties' as the new SDK validator explicitly forbids extra fields
    schema.pop("additionalProperties", None)

    # 2. Walk through schema properties and normalize data types
    properties = schema.get("properties", {})
    for prop_name, prop_meta in properties.items():
        if isinstance(prop_meta, dict):
            prop_type = prop_meta.get("type")
            
            # If the type is an array/list (e.g., ['string', 'null']), resolve it to a single primitive.
            # This directly bypasses the SDK's internal `.upper()` crash on list parameters.
            if isinstance(prop_type, list):
                if "string" in prop_type:
                    prop_meta["type"] = "string"
                elif "integer" in prop_type:
                    prop_meta["type"] = "integer"
                elif "number" in prop_type:
                    prop_meta["type"] = "number"
                elif "boolean" in prop_type:
                    prop_meta["type"] = "boolean"
                else:
                    prop_meta["type"] = prop_type[0]
            
            # Recursively sanitize nested structures within items or sub-properties
            if "items" in prop_meta:
                sanitize_json_schema(prop_meta["items"])
            if "properties" in prop_meta:
                sanitize_json_schema(prop_meta)

    return schema

class GeminiVLM(VLMProvider):
    def __init__(self, model: str | None = None, *, api_key: str | None = None) -> None:
        self.model = model or os.getenv('LLM_MODEL') or os.getenv('GEMINI_VLM_MODEL') or 'gemini-2.5-flash'
        api_key = api_key or os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY') or os.getenv('LLM_API_KEY')
        if not api_key:
            raise ProviderError('GOOGLE_API_KEY is not set.')
        self.client = genai.Client(api_key=api_key)

    def describe(self, image_path: str, prompt: str, *, json_schema: any = None) -> str:
        path = Path(image_path)
        if not path.is_file():
            raise FileNotFoundError(image_path)
        
        try:
            with open(path, 'rb') as f:
                image_bytes = f.read()
                
            config = types.GenerateContentConfig()
            if json_schema is not None:
                config.response_mime_type = "application/json"
                
                # If a raw dictionary (legacy schema format) is supplied, 
                # sanitize it before converting it into a structured types.Schema instance.
                if isinstance(json_schema, dict):
                    import copy
                    clean_schema = sanitize_json_schema(copy.deepcopy(json_schema))
                    config.response_schema = types.Schema(**clean_schema)
                else:
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
        
        # Enforce v1beta API version headers to prevent 404 client errors with text-embedding-004
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