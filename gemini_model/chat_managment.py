from gemini_model.model import GeminiInteract
from gemini_model.query import QueryClassifier
from gemini_model.data.prompts import prompts
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class ChatResponse:
    status: str
    response: str
    prompt_used: Optional[str] = None
    error: Optional[str] = None

class GeminiChatManager:
    def __init__(self, temperature=0.3, max_history_messages=10):
        self.classifier = QueryClassifier(prompts)
        self.model = None
        self.temperature = temperature
        self.max_history_messages = max_history_messages

    def process_request(self, 
                       text_message: str, 
                       media_paths: Optional[List[str]] = None) -> ChatResponse:
        """Procesa una solicitud completa del usuario"""
        try:
            # 1. Clasificar la solicitud para obtener el prompt adecuado
            prompt_key = self.classifier.classify_query(text_message, new_session=True)
            
            # 2. Inicializar o actualizar modelo con el prompt clasificado
            self.model = GeminiInteract(
                prompt_key=prompt_key,
                temperature=self.temperature,
                max_history_messages=self.max_history_messages
            )
            
            # 3. Procesar la solicitud
            if media_paths:
                response = self.model.send_message_with_media(message=text_message, media_paths=media_paths)
            else:
                response = self.model.send_single_message(text_message)

            # 4. Retornar la respuesta
            return ChatResponse(
                status='success',
                response=response.text if hasattr(response, 'text') else response,
                prompt_used=prompt_key
            )

        except Exception as e:
            return ChatResponse(
                status='error',
                response='',
                error=str(e)
            )

    def get_chat_history(self):
        """Retorna el historial de chat si existe un modelo activo"""
        return self.model.chat_history if self.model else None

    def clear_chat(self):
        """Limpia el historial y reinicia el modelo"""
        if self.model:
            self.model.clear_chat()
            self.model = None
    
if __name__ == "__main__":
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
    chat_manager = GeminiChatManager(max_history_messages=10)

    # Ejemplo de conversación
    responses = []
    
    # Mensaje simple
    response = chat_manager.process_request(
        text_message="¿Cómo se dice 'buenos días' en tsafiqui?"
    )
    responses.append(response)

    # Mensaje con multimedia
    response = chat_manager.process_request(
        text_message="Analiza estas imágenes",
        media_paths=[r"C:\Users\Jeremy\Pictures\Screenshots\Captura de pantalla 2024-09-04 233907.png", r"C:\Users\Jeremy\Videos\Grabación 2024-09-23 201954.mp4"]
    )
    responses.append(response)

    # Ver historial
    history = chat_manager.get_chat_history()
    if history:
        print("\nHistorial de la conversación:")
        for msg in history.messages:
            print(f"{msg['role']}: {msg['parts']}")

    # Limpiar al finalizar
    chat_manager.clear_chat()
