from collections import deque
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os
from pathlib import Path

class ChatHistory:
    """Clase para gestionar el historial de chat de una conversación, 
    con capacidad de persistencia en un archivo JSON.

    Attributes:
        max_messages (int): Número máximo de mensajes a almacenar.
        messages (deque): Cola de mensajes, con límite de tamaño.
        history_file (Path): Ruta del archivo donde se guarda el historial.
    """
    def __init__(self, max_messages: int = 10, history_file: str = "chat_history.json"):
        """Inicializa ChatHistory cargando el historial desde el archivo JSON si existe.

        Args:
            max_messages (int): Número máximo de mensajes a almacenar en la cola.
            history_file (str): Nombre del archivo donde se almacena el historial.
        """
        self.max_messages = max_messages
        self.messages = deque(maxlen=max_messages)
        self.history_file = Path(history_file)
        self.media_references = {}  # Almacena {timestamp: [media_files]}
        self.load_history()

    def save_history(self):
        """Guarda el historial y referencias multimedia"""
        history_data = {
            "last_updated": datetime.now().isoformat(),
            "max_messages": self.max_messages,
            "messages": list(self.messages),
            "media_references": self.media_references
        }
        
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving history: {e}")
        
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            print(f"Text conversation history saved to {self.history_file}")
        except Exception as e:
            print(f"Error saving history: {e}")

    def load_history(self):
        """Carga el historial de conversación desde un archivo JSON si existe, 
        y lo almacena en `self.messages`.

        Este método verifica si el archivo existe, y si es así, 
        lee el contenido del archivo JSON y lo carga en la cola `self.messages`.

        Raises:
            Exception: Si ocurre un error al leer o cargar el archivo.
        """
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                    self.messages = deque(history_data.get('messages', []), 
                                       maxlen=self.max_messages)
                    self.media_references = history_data.get('media_references', {})
                print(f"History loaded from {self.history_file}")
            except Exception as e:
                print(f"Error loading history: {e}")
                self.messages = deque(maxlen=self.max_messages)
                self.media_references = {}
        
    def get_formatted_history(self, system_prompt: dict, assistant_prompt: dict) -> List[Dict[str, Any]]:
        """Retorna el historial de mensajes en el formato adecuado para una API (por ejemplo, Gemini).

        Incluye los mensajes de sistema y asistente, seguidos por el historial 
        de mensajes de texto sin multimedia. Esto permite que el historial esté 
        en el formato correcto y limpio para ser procesado externamente.

        Args:
            system_prompt (dict): Mensaje de sistema a incluir al inicio.
            assistant_prompt (dict): Mensaje de asistente a incluir después del system_prompt.

        Returns:
            List[Dict[str, Any]]: Lista de mensajes formateados en un diccionario para el API.
        """
        history = []
        
        # Agregar system prompt si existe
        if system_prompt:
            history.append({
                "role": "model",
                "parts": [system_prompt]
            })
        
        # Agregar assistant prompt si existe
        if assistant_prompt:
            history.append({
                "role": "model",
                "parts": [str(assistant_prompt)]
            })
        
        # Solo incluir mensajes de texto (sin multimedia)
        for message in self.messages:
            if not any(isinstance(part, str) and part.startswith('[Media file:') 
                    for part in message['parts']):
                history.append({
                    "role": message["role"],
                    "parts": message["parts"]
                })
        
        return history

    def add_message(self, role: str, content: Any):
        """Agrega un nuevo mensaje al historial y guarda el historial actualizado en el archivo.

        Este método acepta contenido de texto o una lista de partes (puede incluir referencias
        a archivos multimedia) y lo convierte en un formato adecuado para almacenar. Luego, 
        guarda el historial actualizado llamando a `save_history`.

        Args:
            role (str): Rol del emisor del mensaje, por ejemplo 'user' o 'assistant'.
            content (Any): Contenido del mensaje, que puede ser texto o una lista de partes.
        """
        timestamp = datetime.now().isoformat()
        
        if isinstance(content, list):
            # Separar multimedia y texto
            media_files = []
            text_parts = []
            
            for item in content:
                if hasattr(item, 'uri'):
                    media_files.append({
                        'uri': item.uri,
                        'mime_type': getattr(item, 'mime_type', 'unknown'),
                        'name': item.name
                    })
                    text_parts.append(f"[Media file: {item.mime_type}]")
                else:
                    text_parts.append(str(item))
            
            # Guardar referencias a multimedia
            if media_files:
                self.media_references[timestamp] = media_files
            
            message = {
                "role": role,
                "parts": text_parts,
                "timestamp": timestamp,
                "has_media": bool(media_files)
            }
        else:
            message = {
                "role": role,
                "parts": [str(content)],
                "timestamp": timestamp,
                "has_media": False
            }
        
        self.messages.append(message)
        self.save_history()

    def clear_history(self):
        """Limpia el historial de conversación actual, borra todos los mensajes
        de `self.messages` y guarda el estado vacío en el archivo."""
        self.messages.clear()
        self.save_history()