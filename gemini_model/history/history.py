from collections import deque
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os
from pathlib import Path

class ChatHistory:
    def __init__(self, max_messages: int = 10, history_file: str = "chat_history.json"):
        self.max_messages = max_messages
        self.messages = deque(maxlen=max_messages)
        self.history_file = Path(history_file)
        self.load_history()

    def save_history(self):
        """Guarda solo los mensajes de texto en el historial"""
        history_data = {
            "last_updated": datetime.now().isoformat(),
            "max_messages": self.max_messages,
            "messages": [
                msg for msg in list(self.messages)
                if not any(isinstance(part, dict) and part.get('type') == 'media' 
                          for part in msg['parts'])
            ]
        }
        
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            print(f"Text conversation history saved to {self.history_file}")
        except Exception as e:
            print(f"Error saving history: {e}")

    def load_history(self):
        """Carga el historial de conversación desde JSON"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                    messages = history_data.get('messages', [])
                    self.messages = deque(messages, maxlen=self.max_messages)
                print(f"Conversation history loaded from {self.history_file}")
            except Exception as e:
                print(f"Error loading history: {e}")
                self.messages = deque(maxlen=self.max_messages)

    def get_formatted_history(self, system_prompt: dict, assistant_prompt: dict) -> List[Dict[str, Any]]:
        """Retorna el historial formateado para Gemini"""
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
        
        # Agregar solo mensajes de texto del historial
        for message in self.messages:
            # Filtrar mensajes que no contengan multimedia
            if not any(isinstance(part, dict) and part.get('type') == 'media' 
                      for part in message['parts']):
                history.append({
                    "role": message["role"],
                    "parts": message["parts"]
                })
        
        return history

    def add_message(self, role: str, content: Any):
        """Agrega un nuevo mensaje al historial"""
        if isinstance(content, list):
            # Para mensajes con multimedia, guardar una versión de texto
            text_parts = []
            for item in content:
                if hasattr(item, 'uri'):
                    text_parts.append(f"[Media file: {getattr(item, 'mime_type', 'unknown')}]")
                else:
                    text_parts.append(str(item))
            
            message = {
                "role": role,
                "parts": text_parts,
                "timestamp": datetime.now().isoformat()
            }
        else:
            message = {
                "role": role,
                "parts": [str(content)],
                "timestamp": datetime.now().isoformat()
            }
        
        self.messages.append(message)
        self.save_history()

    def clear_history(self):
        """Limpia el historial de conversación"""
        self.messages.clear()
        self.save_history()