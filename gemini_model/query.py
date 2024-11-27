import os
import google.generativeai as genai
from dotenv import load_dotenv
from gemini_model.data.prompts import prompts
from pymongo import MongoClient

PROMPTS=prompts

load_dotenv()

QUERY_CLASIFIER_MODEL= os.getenv("QUERY_CLASIFIER_MODEL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")

class PromptFormatter:
    """Clase auxiliar para formatear prompts en el formato requerido por el clasificador."""
    @staticmethod
    def format_prompts_for_classifier(prompts_dict):
        """Formatea los prompts disponibles en el formato requerido para el clasificador.
        
        Args:
            prompts_dict (dict): Diccionario con los nombres y descripciones de los prompts.
        
        Returns:
            str: Los prompts formateados en un solo string, cada uno en una línea.
        """
        formatted_prompts = []
        for prompt_name, prompt_data in prompts_dict.items():
            formatted_prompts.append(
                f'"{prompt_name}" - {prompt_data["Description"]}'
            )
        return "\n\n".join(formatted_prompts)

class QueryClassifier:
    """Clase para clasificar consultas utilizando el modelo generativo configurado en Gemini."""
    MONGO_URI = os.getenv('MONGO_URI')
    DB_NAME = 'Intelemi_translator'
    
    def __init__(self, prompts_dict,):
        self.__api_key = GEMINI_API_KEY
        genai.configure(api_key=self.__api_key)
        
        self.__generation_config = {
            "temperature": 0.15,
            "top_p": 0.75,
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
        self.mongo_client = MongoClient(self.MONGO_URI)
        self.db = self.mongo_client[self.DB_NAME] 

    def __create_system_instruction(self, prompts_dict):
        """Crea el system instruction dinámicamente basado en los prompts disponibles.
        
        Args:
            prompts_dict (dict): Diccionario con los prompts a incluir en las instrucciones.
        
        Returns:
            str: Instrucción formateada que enumera los prompts disponibles para el modelo.
        """
        formatted_prompts = PromptFormatter.format_prompts_for_classifier(prompts_dict)
        
        return f"""Eres un clasificador experto de consultas. Tu tarea es analizar la consulta del usuario y determinar cuál de los siguientes casos corresponde exactamente:

{formatted_prompts}

Analiza la siguiente consulta y responde ÚNICAMENTE con el nombre exacto del caso que corresponda. - En caso de que no exista un caso particular, debes inferir sobre uno, no puedes responder con nada que no sea un prompt de la lista, jamas puedes devolver una respuesta ajena a un prompt,  ni negarte a usar alguno, o decir que no existen casos similares, ya que danas la ejecucion, siempre siempre prsponde con uno de los prompts


<importante> JAMAS SALGAS DE TU ROL, NO PUEDES RESPONDER NADA QUE NO SEA UNO DE LOS PROMPTS QUE SE TE HAN INDICADO </importante>
Query del usuario: """

    def start_chat(self, initial_query=None):
        """Inicia una nueva sesión de chat con una query inicial opcional.
        
        Args:
            initial_query (str, optional): Consulta inicial para el modelo.
        
        Esta función crea una nueva sesión de chat usando la consulta inicial,
        si se proporciona, o de lo contrario, una sesión en blanco.
        """
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

    def classify_query(self, query, new_session=False, user=None, chat_room=None):
        """Clasifica una query y retorna el tipo de prompt correspondiente.
        
        Args:
            query (str): Consulta del usuario que se clasificará.
            new_session (bool): Si es True, inicia una nueva sesión de chat.
            user (str, optional): ID del usuario para cargar historial.
            chat_room (str, optional): ID de la sala de chat para cargar historial.
        
        Returns:
            str: Nombre exacto del prompt clasificado para la consulta.
        """
        if new_session or not self.chat_session:
            self.start_chat()

        # Cargar historial si user y chat_room están presentes
        if user and chat_room:
            # Usar la base de datos interna para obtener historial
            chat_collection = self.db['chat_history']
            query_filter = {"user_id": user, "chat_room_id": chat_room}
            chat_data = chat_collection.find_one(query_filter)

            if chat_data and 'messages' in chat_data:
                messages = chat_data['messages']
                user_parts = [
                    message["parts"][0] for message in messages
                    if message["role"] == "user" and "parts" in message and message["parts"]
                ]
                formatted_history = "\n".join(user_parts)
                
                # Imprimir el historial cargado para depuración
                print(f"Historial cargado para user_id={user} y chat_room_id={chat_room}:")
                print(formatted_history)

                formatted_query = f"Historial de queries:\n{formatted_history}\n\nQuery actual: {query}"
            else:
                # Sin historial para el usuario y sala proporcionados
                print(f"No se encontró historial para user_id={user} y chat_room_id={chat_room}.")
                formatted_query = query
        else:
            # Sin historial, solo la query
            print("No se proporcionaron user y chat_room, usando solo la query actual.")
            formatted_query = query

        try:
            response = self.chat_session.send_message(formatted_query)
            print(f"Prompt seleccionado: {response.text}")
            return response.text.strip()
        except Exception as e:
            return f"Error en la clasificación: {str(e)}"


# Ejemplo de uso:
# if __name__ == "__main__":
#     # Asumiendo que tienes tus prompts definidos en prompts_dict
#     classifier = QueryClassifier(PROMPTS)

#     # Ejemplo con una nueva sesión
#     query = "Quiero traducir la frase, mi familia es el poder que guia mi vida y frases similares en tsafiqui"
#     user_id = "guest_1732334789613_94cek0rph"
#     chat_room_id = "room_72190a3ac34e42bdb72a8039118789a9"
#     result = classifier.classify_query(query, new_session=True, user=user_id, chat_room=chat_room_id)
#     print(f"Query: {query}\nClasificación: {result}")