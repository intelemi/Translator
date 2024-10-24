from model import GeminiInteract, MediaHandler
from query import QueryClassifier
from prompts import prompts
from typing import List, Dict, Optional, Union
import time
from dataclasses import dataclass

@dataclass
class MediaItem:
    path: str
    mime_type: str
    file_object: Optional[object] = None

@dataclass
class ChatResponse:
    status: str
    response: str
    prompt_used: Optional[str] = None
    error: Optional[str] = None
    media_info: Optional[Dict] = None

class GeminiChatManager:
    def __init__(self, temperature=0.3):
        self.classifier = QueryClassifier(prompts)
        self.model = None
        self.temperature = temperature
        self.current_media_files = []
        self.media_handler = MediaHandler()

    def _classify_request(self, text_message: str) -> str:
        """Clasifica la solicitud del usuario basándose solo en el texto"""
        try:
            return self.classifier.classify_query(text_message, new_session=True)
        except Exception as e:
            raise Exception(f"Error en la clasificación: {str(e)}")

    def _prepare_media(self, media_paths: List[str]) -> List[MediaItem]:
        """Prepara y valida los archivos multimedia"""
        media_items = []
        for path in media_paths:
            mime_type = self.media_handler.get_mime_type(path)
            media_items.append(MediaItem(path=path, mime_type=mime_type))
        return media_items

    def _initialize_model(self, prompt_key: str):
        """Inicializa o actualiza el modelo con el prompt correcto"""
        self.model = GeminiInteract(
            prompt_key=prompt_key,
            temperature=self.temperature
        )

    def process_request(self, 
                       text_message: str, 
                       media_paths: Optional[List[str]] = None) -> ChatResponse:
        """
        Procesa una solicitud completa del usuario.
        
        Args:
            text_message: El mensaje de texto del usuario
            media_paths: Lista opcional de rutas a archivos multimedia
            
        Returns:
            ChatResponse con el resultado de la operación
        """
        try:
            # 1. Clasificar la solicitud (solo basándose en el texto)
            prompt_key = self._classify_request(text_message)
            
            # 2. Inicializar modelo con el prompt correcto
            self._initialize_model(prompt_key)
            
            # 3. Procesar la solicitud según si tiene multimedia o no
            if media_paths:
                response = self.model.send_message_with_media(
                    message=text_message,
                    media_paths=media_paths
                )
            else:
                response = self.model.send_single_message(text_message)

            return ChatResponse(
                status='success',
                response=response.text,
                prompt_used=prompt_key,
                media_info={
                    'files_processed': len(media_paths) if media_paths else 0,
                    'mime_types': [self.media_handler.get_mime_type(path) 
                                 for path in (media_paths or [])]
                }
            )

        except Exception as e:
            return ChatResponse(
                status='error',
                response='',
                error=str(e)
            )

    def cleanup(self):
        """Limpia recursos y archivos temporales"""
        if self.model:
            self.model.clear_uploaded_files()
        self.current_media_files = []

# Ejemplo de uso con Gradio (preparación):
def prepare_gradio_interface(chat_manager: GeminiChatManager):
    def process_interaction(message: str, files: List[str] = None) -> Dict:
        response = chat_manager.process_request(
            text_message=message,
            media_paths=files if files else None
        )
        
        # Formatear la respuesta para Gradio
        return {
            'response': response.response,
            'status': response.status,
            'error': response.error if response.error else '',
            'prompt_used': response.prompt_used if response.prompt_used else '',
            'media_info': response.media_info if response.media_info else {}
        }

    # Aquí irá la configuración de la interfaz Gradio
    # (lo implementaremos en la siguiente fase)
    
if __name__ == "__main__":
    # Inicializar el manager
    chat_manager = GeminiChatManager()

    # Ejemplo sin multimedia
    response = chat_manager.process_request(
        text_message="¿Cómo se dice 'buenos días' en tsafiqui?"
    )
    print(f"Respuesta: {response.response}")

    # Ejemplo con multimedia
    response = chat_manager.process_request(
        text_message="¿Qué ves en estas imágenes?",
        media_paths=[r"C:\Users\Jeremy\Pictures\Screenshots\Captura de pantalla 2024-07-12 200220.png", r"C:\Users\Jeremy\Videos\Captures\Alien_ Isolation 2024-10-20 21-54-46.mp4"]
    )
    print(f"Respuesta con multimedia: {response.response}")
    print(f"Info multimedia: {response.media_info}")

    # Limpieza al finalizar
    chat_manager.cleanup()