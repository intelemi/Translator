from dataclasses import dataclass
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import google.generativeai as genai
from google.generativeai import caching

@dataclass
class CacheMetadata:
    cache_id: Optional[str] = None
    created_at: Optional[datetime] = None
    duration_hours: int = 5
    token_count: Optional[int] = None

class CacheRegistry:
    """Maneja el registro persistente de cachés"""
    def __init__(self, registry_path="cache_registry.json"):
        self.registry_path = Path(registry_path)
        self.registry = self._load_registry()

    def _load_registry(self) -> dict:
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading cache registry: {e}")
                return {}
        return {}

    def save_cache_info(self, prompt_key: str, cache_type: str, cache_info: dict):
        if prompt_key not in self.registry:
            self.registry[prompt_key] = {}
        
        self.registry[prompt_key][cache_type] = cache_info
        
        try:
            with open(self.registry_path, 'w') as f:
                json.dump(self.registry, f, indent=2)
            print(f"Cache info saved for {prompt_key}/{cache_type}")
        except Exception as e:
            print(f"Error saving cache registry: {e}")

    def get_cache_info(self, prompt_key: str, cache_type: str) -> Optional[dict]:
        return self.registry.get(prompt_key, {}).get(cache_type)

    def is_cache_valid(self, prompt_key: str, cache_type: str) -> bool:
        cache_info = self.get_cache_info(prompt_key, cache_type)
        if not cache_info:
            return False

        try:
            created_at = datetime.fromisoformat(cache_info['created_at'])
            duration_hours = cache_info['duration']
            return datetime.now() < created_at + timedelta(hours=duration_hours)
        except:
            return False

class PromptCacheManager:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._cache_threshold = 32768
        self.cache_registry = CacheRegistry()

    def _count_tokens(self, content: str) -> int:
        """Estima el conteo de tokens en el contenido"""
        try:
            # Si el contenido es un diccionario o lista, convertirlo a string
            if isinstance(content, (dict, list)):
                content = str(content)
            # Estimación aproximada: 1 token ≈ 4 caracteres
            return len(content) // 4
        except Exception as e:
            print(f"Error counting tokens: {e}")
            return 0

    def _verify_cache_creation(self, cache_id: str) -> bool:
        try:
            cache = caching.CachedContent.get(cache_id)
            if cache and cache.expire_time > datetime.now():
                print(f"Cache verified successfully: {cache_id}")
                print(f"Token count: {cache.usage_metadata.total_token_count}")
                print(f"Expires at: {cache.expire_time}")
                return True
        except Exception as e:
            print(f"Cache verification failed: {e}")
        return False

    def _create_cache(self, content: str, prompt_key: str, cache_type: str) -> Optional[CacheMetadata]:
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

            if cache and cache.usage_metadata.total_token_count > 0:
                cache_info = {
                    "cache_id": cache.name,
                    "created_at": datetime.now().isoformat(),
                    "token_count": cache.usage_metadata.total_token_count,
                    "duration": 5,
                    "display_name": display_name
                }
                
                self.cache_registry.save_cache_info(
                    prompt_key=prompt_key,
                    cache_type=cache_type,
                    cache_info=cache_info
                )
                
                print(f"Cache created and registered: {cache.name}")
                print(f"Token count: {cache_info['token_count']}")
                return CacheMetadata(
                    cache_id=cache.name,
                    created_at=datetime.now(),
                    token_count=cache_info['token_count']
                )
            
        except Exception as e:
            print(f"Cache creation error: {e}")
        return None

    def get_or_create_cache(self, prompt_data: Dict[str, Any], cache_type: str, prompt_key: str) -> Optional[str]:
        # Verificar caché existente en el registro
        if self.cache_registry.is_cache_valid(prompt_key, cache_type):
            cache_info = self.cache_registry.get_cache_info(prompt_key, cache_type)
            try:
                cache = caching.CachedContent.get(cache_info['cache_id'])
                print(f"Using existing cache: {cache_info['display_name']}")
                print(f"Token count: {cache_info['token_count']}")
                return cache_info['cache_id']
            except Exception as e:
                print(f"Error accessing existing cache: {e}")

        # Crear nueva caché si es necesario
        content = prompt_data.get(cache_type)
        if content:
            new_cache = self._create_cache(content, prompt_key, cache_type)
            return new_cache.cache_id if new_cache else None

        return None