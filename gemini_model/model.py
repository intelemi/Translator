import google.generativeai as genai
import gemini_model.prompts as prompts
from dotenv import load_dotenv
import os

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")

genai.configure(api_key=GEMINI_API_KEY)

class GeminiInteract:
    def __init__(self, prompt_key='profesional', 
                 temperature=1, top_p=0.95, 
                 top_k=40, 
                 max_output_tokens=8192):
        self.__model = MODEL_NAME
        self.__system_prompt = self.load_prompt(prompt_key)
        self.__generation_config = {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "max_output_tokens": max_output_tokens,
            "response_mime_type": "text/plain",
        }
        self.chat_session = None

    def load_prompt(self, prompt_key):
        return prompts.prompts.get(prompt_key, "Default system instruction")

    def start_chat(self):
        if not self.chat_session:
            model = genai.GenerativeModel(
                model_name=self.__model,
                generation_config=self.__generation_config,
                system_instruction=self.__system_prompt,
            )
            print(self.__system_prompt)
            self.chat_session = model.start_chat()

    def send_single_message(self, message):
        self.start_chat() 
        try:
            response = self.chat_session.send_message(message)
            return response
        except Exception as e:
            return f"Error: {str(e)}"


if __name__ == "__main__":
    gemini = GeminiInteract(prompt_key='creativo')
    response = gemini.send_single_message(message='¿Qué puedes hacer por mí?')
    print(response.text)
