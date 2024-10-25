from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from google.generativeai import caching


import json
import os
from pathlib import Path

class CacheStorage:
    """Maneja el almacenamiento persistente de metadatos de caché"""
    def __init__(self, storage_path="cache_metadata.json"):
        self.storage_path = Path(storage_path)
        self.cache_data = self._load_cache_data()

    def _load_cache_data(self):
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_cache_metadata(self, prompt_key: str, cache_type: str, metadata: dict):
        if prompt_key not in self.cache_data:
            self.cache_data[prompt_key] = {}
        self.cache_data[prompt_key][cache_type] = metadata
        
        with open(self.storage_path, 'w') as f:
            json.dump(self.cache_data, f, indent=2)

    def get_cache_metadata(self, prompt_key: str, cache_type: str) -> Optional[dict]:
        return self.cache_data.get(prompt_key, {}).get(cache_type)

@dataclass
class CacheMetadata:
    cache_id: Optional[str] = None
    created_at: Optional[datetime] = None
    duration_hours: int = 5
    token_count: Optional[int] = None

    @property
    def is_valid(self) -> bool:
        if not all([self.cache_id, self.created_at]):
            return False
        return datetime.now() < self.created_at + timedelta(hours=self.duration_hours)

class PromptCacheManager:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._cache_threshold = 32768
        self.cache_storage = CacheStorage()

    def _count_tokens(self, content: str) -> int:
        """Estima el conteo de tokens en el contenido"""
        # Estimación aproximada: 1 token ≈ 4 caracteres
        return len(str(content)) // 4

    def _verify_cache_creation(self, cache_id: str) -> bool:
        """Verifica si la caché se creó correctamente"""
        try:
            cache = caching.CachedContent.get(cache_id)
            if cache and cache.state.name == "ACTIVE":
                print(f"Cache verified successfully: {cache_id}")
                print(f"Token count: {cache.usage_metadata.get('total_token_count', 'unknown')}")
                return True
        except Exception as e:
            print(f"Cache verification failed: {e}")
        return False

    def _create_cache(self, content: str, prompt_key: str, cache_type: str) -> Optional[CacheMetadata]:
        """Crea una nueva caché con verificación"""
        token_count = self._count_tokens(content)
        print(f"Estimated token count for {cache_type}: {token_count}")
        
        if token_count < self._cache_threshold:
            print(f"Content too small for caching ({token_count} < {self._cache_threshold} tokens)")
            return None

        try:
            display_name = f"{prompt_key}_{cache_type}_cache"
            print(f"Creating cache for {display_name}...")
            
            cache = caching.CachedContent.create(
                model=self.model_name,
                display_name=display_name,
                contents=[content],
                ttl=timedelta(hours=5)
            )

            if self._verify_cache_creation(cache.name):
                metadata = CacheMetadata(
                    cache_id=cache.name,
                    created_at=datetime.now(),
                    token_count=token_count
                )
                
                # Guardar metadata
                self.cache_storage.save_cache_metadata(
                    prompt_key=prompt_key,
                    cache_type=cache_type,
                    metadata={
                        "cache_id": cache.name,
                        "created_at": metadata.created_at.isoformat(),
                        "token_count": token_count,
                        "duration_hours": metadata.duration_hours
                    }
                )
                
                return metadata
            
        except Exception as e:
            print(f"Cache creation error: {e}")
        return None

    def get_or_create_cache(self, prompt_data: Dict[str, Any], cache_type: str, prompt_key: str) -> Optional[str]:
        """Obtiene o crea caché para un tipo específico de contenido"""
        content = prompt_data.get(cache_type)
        if not content:
            return None

        # Verificar caché existente
        stored_metadata = self.cache_storage.get_cache_metadata(prompt_key, cache_type)
        if stored_metadata:
            try:
                existing_cache = caching.CachedContent.get(stored_metadata['cache_id'])
                if existing_cache and datetime.now() < datetime.fromisoformat(stored_metadata['created_at']) + timedelta(hours=stored_metadata['duration_hours']):
                    if self._verify_cache_creation(existing_cache.name):
                        print(f"Using existing cache for {cache_type}: {existing_cache.name}")
                        return existing_cache.name
            except Exception as e:
                print(f"Error checking existing cache: {e}")

        # Crear nueva caché
        new_cache = self._create_cache(content, prompt_key, cache_type)
        return new_cache.cache_id if new_cache else None