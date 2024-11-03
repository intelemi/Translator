import os
import time
from data.prompts import prompts
from dotenv import load_dotenv
import google.generativeai as genai
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from google.generativeai import caching
from cache.cache import CacheMetadata,PromptCacheManager
from history.history import ChatHistory
from media.media_handler import MediaHandler

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")


genai.configure(api_key=GEMINI_API_KEY)


class GeminiInteract:
    def __init__(self, prompt_key='query_translation_spanish_to_tsafiqui', 
                 temperature=0.1, top_p=0.95, 
                 top_k=40, 
                 max_output_tokens=8192,
                 max_history_messages=10,
                 history_file="./gemini_model/history/chat_history.json"):
        
        self.__model = MODEL_NAME
        self.__prompt_key = prompt_key 
        self.__prompt_config = prompts[prompt_key]  # Acceso directo al diccionario de prompts
        self.__generation_config = {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "max_output_tokens": max_output_tokens,
            "response_mime_type": "text/plain",
        }
        self.chat_session = None
        self.media_handler = MediaHandler()
        self.cache_manager = PromptCacheManager(MODEL_NAME)
        self.chat_history = ChatHistory(
            max_messages=max_history_messages,
            history_file=history_file
        )
        
    def _initialize_model_with_cache(self):
        """Inicializa el modelo con caché del system prompt"""
        system_cache_id = self.cache_manager.get_or_create_cache(
            self.__prompt_config, 'system', self.__prompt_key
        )

        if system_cache_id:
            try:
                print("Initializing model with cached system prompt...")
                system_cache = caching.CachedContent.get(system_cache_id)
                return genai.GenerativeModel.from_cached_content(
                    cached_content=system_cache,
                    generation_config=self.__generation_config
                )
            except Exception as e:
                print(f"Cache initialization error: {e}")

        print("Using standard model initialization...")
        return genai.GenerativeModel(
            model_name=self.__model,
            generation_config=self.__generation_config,
            system_instruction=self.__prompt_config['system']
        )


    def start_chat(self):
        if not self.chat_session:
            print("\nInitializing chat session...")
            model = self._initialize_model_with_cache()

            # Primero manejar las cachés
            assistant_cache_id = None
            if self.__prompt_config.get('assistant'):
                assistant_cache_id = self.cache_manager.get_or_create_cache(
                    self.__prompt_config, 'assistant', self.__prompt_key
                )
                
                if assistant_cache_id:
                    try:
                        cache = caching.CachedContent.get(assistant_cache_id)
                        print(f"Using cached assistant content (Token count: {cache.usage_metadata.total_token_count})")
                    except Exception as e:
                        print(f"Error accessing assistant cache: {e}")

            # Obtener el historial formateado excluyendo mensajes con multimedia
            formatted_history = self.chat_history.get_formatted_history(
                system_prompt=self.__prompt_config.get('system'),
                assistant_prompt=self.__prompt_config.get('assistant')
            )

            # Iniciar sesión con el historial completo
            self.chat_session = model.start_chat(history=formatted_history)
            print("Chat session initialized successfully")

    def process_media_files(self, media_paths):
        """Procesa y carga archivos multimedia"""
        files = []
        for path in media_paths:
            # Usar get_or_upload_file en lugar de upload_file
            file = self.media_handler.get_or_upload_file(path)
            if file:
                files.append(file)

        # Esperar solo si hay archivos de video
        if any(file.mime_type.startswith('video/') for file in files):
            self.media_handler.wait_for_files_active(files)
        
        return files

    def send_message_with_media(self, message, media_paths=None):
        """Envía un mensaje que puede incluir archivos multimedia"""
        try:
            print("\nInitializing chat session for multimedia message...")
            model = self._initialize_model_with_cache()

            # Manejar cachés
            if self.__prompt_config.get('assistant'):
                assistant_cache_id = self.cache_manager.get_or_create_cache(
                    self.__prompt_config, 'assistant', self.__prompt_key
                )
                
                if assistant_cache_id:
                    try:
                        cache = caching.CachedContent.get(assistant_cache_id)
                        print(f"Using cached assistant content (Token count: {cache.usage_metadata.total_token_count})")
                    except Exception as e:
                        print(f"Error accessing assistant cache: {e}")

            message_parts = []
            
            if media_paths:
                # Procesar archivos multimedia
                files = self.process_media_files(media_paths)
                if files:
                    message_parts.extend(files)
                    print(f"Added {len(files)} media files to message")
            
            message_parts.append(message)
            
            # Iniciar sesión con prompts iniciales
            initial_history = []
            if self.__prompt_config.get('system'):
                initial_history.append({
                    "role": "model",
                    "parts": [self.__prompt_config['system']]
                })
            if self.__prompt_config.get('assistant'):
                initial_history.append({
                    "role": "model",
                    "parts": [str(self.__prompt_config['assistant'])]
                })
            
            # Crear nueva sesión
            self.chat_session = model.start_chat(history=initial_history)
            
            # Enviar mensaje
            print("Sending message with media...")
            response = self.chat_session.send_message(message_parts)
            
            # Guardar en historial
            self.chat_history.add_message("user", message_parts)
            if hasattr(response, 'text'):
                self.chat_history.add_message("model", response.text)
                print("Message processed successfully")
            
            return response
        except Exception as e:
            error_msg = f"Error processing multimedia message: {str(e)}"
            print(error_msg)
            return error_msg

    def clear_uploaded_files(self):
        """Limpia el registro de archivos subidos"""
        self.uploaded_files = []

    def send_single_message(self, message):
        self.start_chat() 
        try:
            # Agregar mensaje del usuario al historial
            self.chat_history.add_message("user", message)
            
            # Enviar mensaje y obtener respuesta
            response = self.chat_session.send_message(message)
            
            # Agregar la respuesta al historial
            if hasattr(response, 'text'):
                self.chat_history.add_message("model", response.text)
            
            return response
        except Exception as e:
            return f"Error: {str(e)}"
        
        
    def clear_chat(self):
        """Limpia el historial y reinicia la sesión"""
        self.chat_history.clear_history()
        self.chat_session = None
        self.media_handler.clear_cache()
        


if __name__ == "__main__":
    gemini = GeminiInteract(
        prompt_key='query_translation_spanish_to_tsafiqui',
        max_history_messages=10
    )
    
    # Rutas de archivos para reutilizar
    media_paths = [
        r"C:\Users\Jeremy\Videos\Grabación 2024-09-23 201954.mp4",
        r"C:\Users\Jeremy\Pictures\Screenshots\Captura de pantalla 2024-09-04 233907.png"
    ]
    photos = [
        r"C:\Users\Jeremy\Pictures\Screenshots\Captura de pantalla 2024-09-04 233907.png"
    ]
    videos=[
         r"C:\Users\Jeremy\Videos\Grabación 2024-09-23 201954.mp4"
    ]
    
    # Ejemplo 1: Primera carga de multimedia
    # print("\n=== Ejemplo 1: Primera carga de multimedia ===")
    # response = gemini.send_message_with_media(
    #     message="Analiza estos archivos multimedia y haz la transcripcion a tsafiqui",
    #     media_paths=media_paths
    # )
    # print("Respuesta:", response.text)

    # Ejemplo 2: Reutilización de multimedia
    print("\n=== Ejemplo 2: Reutilización de multimedia ===")
    response = gemini.send_message_with_media(
        message="describe este archivo con más detalle",
        media_paths= videos  # Mismos archivos, debería usar caché
    )
    print("Respuesta:", response.text)

    # # Ejemplo 3: Mensaje de texto simple
    # print("\n=== Ejemplo 3: Mensaje simple ===")
    # response = gemini.send_single_message(
    #     "Que mas me puedes decir de eso? recuerda que debes traducirlo al tsafiqui"
    # )
    # print("Respuesta:", response.text)

    # Mostrar historial con referencias multimedia
    # print("\n=== Historial de la conversación ===")
    # for msg in gemini.chat_history.messages:
    #     timestamp = datetime.fromisoformat(msg['timestamp']).strftime("%H:%M:%S")
    #     role = "Usuario" if msg['role'] == "user" else "Asistente"
        
    #     print(f"\n[{timestamp}] {role}:")
    #     if msg.get('has_media'):
    #         media_refs = gemini.chat_history.media_references.get(msg['timestamp'], [])
    #         for media in media_refs:
    #             print(f"[Media: {media['mime_type']} - {media['uri']}]")
        
    #     # Mostrar texto del mensaje
    #     for part in msg['parts']:
    #         if isinstance(part, str) and not part.startswith('[Media file:'):
    #             print(part)

    # Ejemplo de limpieza
    # gemini.clear_chat()