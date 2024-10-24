import time
import google.generativeai as genai
from google.generativeai import caching
from prompts import prompts
from dotenv import load_dotenv
import os

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
                 max_output_tokens=8192):
        self.__model = MODEL_NAME
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

    def start_chat(self):
        if not self.chat_session:
            print(f"\nInitializing chat with:")
            print(f"System prompt: {self.__prompt_config['system'][:100]}...")
            if self.__prompt_config.get('assistant'):
                print(f"Assistant prompt: {self.__prompt_config['assistant'][:100]}...")
            
            model = genai.GenerativeModel(
                model_name=self.__model,
                generation_config=self.__generation_config,
                system_instruction=self.__prompt_config['system']
            )

            initial_history = []
            if self.__prompt_config.get('assistant'):
                initial_history = [
                    {
                        "role": "model",
                        "parts": [str(self.__prompt_config['assistant'])]
                    }
                ]

            self.chat_session = model.start_chat(history=initial_history)
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
            
            # Procesar archivos multimedia si existen
            if media_paths:
                files = self.process_media_files(media_paths)
                message_parts.extend(files)
            
            # Agregar el texto del mensaje
            message_parts.append(message)
            
            # Enviar el mensaje con todas las partes
            response = self.chat_session.send_message(message_parts)
            return response
        except Exception as e:
            return f"Error: {str(e)}"

    def clear_uploaded_files(self):
        """Limpia el registro de archivos subidos"""
        self.uploaded_files = []

    def send_single_message(self, message):
        self.start_chat() 
        try:
            response = self.chat_session.send_message(message)
            return response
        except Exception as e:
            return f"Error: {str(e)}"
        


if __name__ == "__main__":
    gemini = GeminiInteract(prompt_key='query_translation_spanish_to_tsafiqui')
    
    # Ejemplo con mezcla de videos e imágenes
    response = gemini.send_message_with_media(
        message="Analiza estos archivos multimedia y haz la transcripcion a tsafiqui",
        media_paths=[
            r"C:\Users\Jeremy\Videos\Grabación 2024-09-23 201954.mp4",
            r"C:\Users\Jeremy\Pictures\Screenshots\Captura de pantalla 2024-07-12 200220.png",
            r"C:\Users\Jeremy\Videos\Captures\Alien_ Isolation 2024-10-20 21-54-46.mp4"
        ]
    )
    print(response.text)