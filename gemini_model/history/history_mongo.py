from pymongo import MongoClient
from datetime import datetime
import google.generativeai as genai


class ChatHistoryMongo:
    """
    Clase para gestionar el historial de chat de una conversación, con capacidad de persistencia en MongoDB.
    """
    def __init__(self, db_uri, db_name, user_id, chat_room_id, max_messages=10):
        self.client = MongoClient(db_uri)
        self.db = self.client[db_name]
        self.chat_collection = self.db['chat_history']
        self.user_id = user_id
        self.chat_room_id = chat_room_id
        self.max_messages = max_messages

    def _get_chat_query(self):
        """Genera la consulta para la sala de chat y el usuario."""
        return {"user_id": self.user_id, "chat_room_id": self.chat_room_id}

    def load_history(self):
        """
        Carga el historial de mensajes desde MongoDB y los devuelve en formato adecuado para el modelo.
        """
        chat_data = self.chat_collection.find_one(self._get_chat_query())
        if chat_data and 'messages' in chat_data:
            return chat_data['messages']
        return []

    def get_formatted_history(self, system_prompt=None, assistant_prompt=None):
        """
        Retorna el historial de mensajes en el formato adecuado para una API (por ejemplo, Gemini).
        
        Incluye los mensajes de sistema y asistente, seguidos por el historial 
        de mensajes de texto sin multimedia.
        
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

        # Cargar historial de la base de datos
        messages = self.load_history()
        for message in messages:
            if not message.get("has_media", False):
                history.append({
                    "role": message["role"],
                    "parts": message["parts"]
                })

        return history

    def add_message(self, role, content):
        """
        Agrega un nuevo mensaje al historial en MongoDB.

        Args:
            role (str): Rol del emisor del mensaje, por ejemplo 'user' o 'assistant'.
            content (Any): Contenido del mensaje, que puede ser texto o una lista de partes.
        """
        timestamp = datetime.now().isoformat()

        if isinstance(content, list):
            media_files = [item for item in content if hasattr(item, 'uri')]
            text_parts = [f"[Media file: {item.mime_type}]" if hasattr(item, 'uri') else str(item) for item in content]
        else:
            media_files = []
            text_parts = [str(content)]

        message = {
            "role": role,
            "parts": text_parts,
            "timestamp": timestamp,
            "has_media": bool(media_files)
        }

        # Actualizar la base de datos
        query = self._get_chat_query()
        update = {
            "$push": {
                "messages": {
                    "$each": [message],
                    "$slice": -self.max_messages  # Mantener solo los últimos max_messages
                }
            }
        }
        self.chat_collection.update_one(query, update, upsert=True)

