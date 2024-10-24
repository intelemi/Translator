import os
import google.generativeai as genai
from dotenv import load_dotenv
from prompts import prompts

PROMPTS=prompts

load_dotenv()

QUERY_CLASIFIER_MODEL= os.getenv("QUERY_CLASIFIER_MODEL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")

class PromptFormatter:
    @staticmethod
    def format_prompts_for_classifier(prompts_dict):
        """Formatea los prompts disponibles en el formato requerido para el clasificador"""
        formatted_prompts = []
        for prompt_name, prompt_data in prompts_dict.items():
            formatted_prompts.append(
                f'"{prompt_name}" - {prompt_data["Description"]}'
            )
        return "\n\n".join(formatted_prompts)

class QueryClassifier:
    def __init__(self, prompts_dict):
        self.__api_key = GEMINI_API_KEY
        genai.configure(api_key=self.__api_key)
        
        self.__generation_config = {
            "temperature": 0.2,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }
        
        self.__system_instruction = self.__create_system_instruction(prompts_dict)
        
        self.__model = genai.GenerativeModel(
            model_name=QUERY_CLASIFIER_MODEL,
            generation_config=self.__generation_config,
            system_instruction=self.__system_instruction,
        )
        
        self.chat_session = None

    def __create_system_instruction(self, prompts_dict):
        """Crea el system instruction dinámicamente basado en los prompts disponibles"""
        formatted_prompts = PromptFormatter.format_prompts_for_classifier(prompts_dict)
        
        return f"""Eres un clasificador experto de consultas. Tu tarea es analizar la consulta del usuario y determinar cuál de los siguientes casos corresponde exactamente:

{formatted_prompts}

Analiza la siguiente consulta y responde ÚNICAMENTE con el nombre exacto del caso que corresponda.

Query del usuario:"""

    def start_chat(self, initial_query=None):
        """Inicia una nueva sesión de chat con una query inicial opcional"""
        if initial_query:
            history = [
                {
                    "role": "model",
                    "parts": [initial_query],
                }
            ]
            self.chat_session = self.__model.start_chat(history=history)
        else:
            self.chat_session = self.__model.start_chat()

    def classify_query(self, query, new_session=False):
        """Clasifica una query y retorna el tipo de prompt correspondiente"""
        if new_session or not self.chat_session:
            self.start_chat()
        
        try:
            response = self.chat_session.send_message(query)
            print(f"Prompt seleccionado :{response.text} ")
            return response.text.strip()
        except Exception as e:
            return f"Error en la clasificación: {str(e)}"

# Ejemplo de uso:
if __name__ == "__main__":
    # Asumiendo que tienes tus prompts definidos en prompts_dict
    classifier = QueryClassifier(PROMPTS)

    # Ejemplo con una nueva sesión
    query = "Quiero traducir la frase, mi familia es el poder que guia mi vida y frases similares en tsafiqui"
    result = classifier.classify_query(query, new_session=True)
    print(f"Query: {query}\nClasificación: {result}")
