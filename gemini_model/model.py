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


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")


genai.configure(api_key=GEMINI_API_KEY)



class MediaHandler:
    """Clase auxiliar para manejar la carga y procesamiento de archivos multimedia"""
    @staticmethod
    def get_mime_type(file_path):
        """Determina el tipo MIME basado en la extensión del archivo"""
        extension = file_path.lower().split('.')[-1]
        mime_types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'mp4': 'video/mp4',
            'avi': 'video/x-msvideo',
            'mov': 'video/quicktime'
        }
        return mime_types.get(extension, 'application/octet-stream')

    @staticmethod
    def upload_file(path):
        """Sube un archivo a Gemini"""
        mime_type = MediaHandler.get_mime_type(path)
        try:
            file = genai.upload_file(path, mime_type=mime_type)
            print(f"Uploaded file '{file.display_name}' as: {file.uri}")
            return file
        except Exception as e:
            print(f"Error uploading file: {str(e)}")
            return None

    @staticmethod
    def wait_for_files_active(files, polling_interval=10):
        """Espera a que los archivos estén activos"""
        print("Waiting for file processing...")
        for name in (file.name for file in files):
            file = genai.get_file(name)
            while file.state.name == "PROCESSING":
                print(".", end="", flush=True)
                time.sleep(polling_interval)
                file = genai.get_file(name)
            if file.state.name != "ACTIVE":
                raise Exception(f"File {file.name} failed to process")
        print("...all files ready")
        print()


class GeminiInteract:
    def __init__(self, prompt_key='query_no_translation_tsafiqui', 
                 temperature=0.3, top_p=0.95, 
                 top_k=40, 
                 max_output_tokens=8192,
                 max_history_messages=10,
                 history_file="chat_history.json"):
        
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
        self.uploaded_files = []
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

            # Obtener el historial formateado incluyendo los prompts actuales
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
            file = self.media_handler.upload_file(path)
            if file:
                files.append(file)
                self.uploaded_files.append(file)

        # Esperar solo si hay archivos de video
        if any(file.mime_type.startswith('video/') for file in files):
            self.media_handler.wait_for_files_active(files)
        
        return files

    def process_media_files(self, media_paths):
        """Procesa y carga archivos multimedia"""
        files = []
        for path in media_paths:
            file = self.media_handler.upload_file(path)
            if file:
                files.append(file)
                self.uploaded_files.append(file)

        # Esperar solo si hay archivos de video
        if any(file.mime_type.startswith('video/') for file in files):
            self.media_handler.wait_for_files_active(files)
        
        return files

    def send_message_with_media(self, message, media_paths=None):
        """Envía un mensaje que puede incluir archivos multimedia"""
        self.start_chat()
        
        try:
            message_parts = []
            
            if media_paths:
                files = self.process_media_files(media_paths)
                message_parts.extend(files)
            
            message_parts.append(message)
            
            # Agregar mensaje del usuario al historial
            self.chat_history.add_message("user", message_parts)
            
            # Enviar el mensaje
            response = self.chat_session.send_message(message_parts)
            
            # Agregar respuesta al historial
            self.chat_history.add_message("model", response.text)
            
            return response
        except Exception as e:
            error_msg = f"Error: {str(e)}"
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
            
            # Enviar mensaje
            response = self.chat_session.send_message(message)
            
            # Agregar respuesta al historial
            self.chat_history.add_message("model", response.text)
            
            return response
        except Exception as e:
            return f"Error: {str(e)}"
        
        
    def clear_chat(self):
        """Limpia el historial y reinicia la sesión"""
        self.chat_history.clear_history()
        self.chat_session = None
        self.clear_uploaded_files()
        


if __name__ == "__main__":
    gemini = GeminiInteract(
        prompt_key='query_no_translation_spanish_with_tsafiqui_terms',
        max_history_messages=10
    )
    
    # Primer mensaje con multimedia
    print("\n=== Primera interacción (con multimedia) ===")
    response = gemini.send_message_with_media(
        message="ahora analiza estos archivos multimedia y haz la transcripcion a tsafiqui",
        media_paths=[
            r"C:\Users\JeremyCollaguazo\Videos\Grabaciones de pantalla\Grabación de pantalla 2024-08-12 092424.mp4",
            r"C:\Users\JeremyCollaguazo\Pictures\Screenshots\Captura de pantalla 2023-12-29 113600.png"
        ]
    )
    print("Respuesta:", response.text)

    # Mensaje de seguimiento (solo texto)
    print("\n=== Segunda interacción (solo texto) ===")
    response = gemini.send_single_message(
        "Basándote en la transcripción anterior, ¿podrías explicar más sobre el significado en tsafiqui?"
    )
    print("Respuesta:", response.text)

    # Otro mensaje de texto
    print("\n=== Tercera interacción (solo texto) ===")
    response = gemini.send_single_message(
        "¿Cómo se pronuncia correctamente esa frase en tsafiqui?"
    )
    print("Respuesta:", response.text)

    # Ver historial actual
    print("\n=== Historial de la conversación ===")
    for msg in gemini.chat_history.messages:
        role = "Usuario" if msg['role'] == "user" else "Asistente"
        content = msg['parts'][0] if isinstance(msg['parts'][0], str) else "[Contenido multimedia]"
        timestamp = datetime.fromisoformat(msg['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{timestamp} - {role}:")
        print(content)

    # Opcional: Guardar o limpiar historial
    # gemini.clear_chat()