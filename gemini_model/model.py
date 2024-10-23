import google.generativeai as genai
from google.generativeai import caching
from prompts import prompts
from dotenv import load_dotenv
import os

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")


genai.configure(api_key=GEMINI_API_KEY)

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

    def start_chat(self):
        if not self.chat_session:
            # Crear el modelo con la configuración del sistema
            model = genai.GenerativeModel(
                model_name=self.__model,
                generation_config=self.__generation_config,
                system_instruction=self.__prompt_config['system']
            )

            # Iniciar el chat con el diccionario como primer mensaje del modelo
            initial_history = []
            if self.__prompt_config.get('assistant'):
                initial_history = [
                    {
                        "role": "model",
                        "parts": [str(self.__prompt_config['assistant'])]
                    }
                ]

            self.chat_session = model.start_chat(history=initial_history)
            print(f"System Prompt loaded: {self.__prompt_config['system'][:50]}...")

    def send_single_message(self, message):
        self.start_chat() 
        try:
            response = self.chat_session.send_message(message)
            return response
        except Exception as e:
            return f"Error: {str(e)}"
        


if __name__ == "__main__":
    gemini = GeminiInteract(prompt_key='query_translation_tsafiqui_to_spanish')
    response = gemini.send_single_message(message='¿Qué puedes hacer por mí?')
    print(response.text)