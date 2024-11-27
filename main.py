from flask import Flask, request, jsonify
from gemini_model.chat_managment import GeminiChatManager
from gemini_model.model import GeminiInteract
from gemini_model.history.history_mongo import ChatHistoryMongo
from dotenv import load_dotenv
import os
import uuid
import time
import shutil
import tempfile
import threading
from flask_cors import CORS
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

app = Flask(__name__)
CORS(app) 
gemini_chat_manager = GeminiChatManager(max_history_messages=20)

# Ruta temporal para almacenar los archivos multimedia
TEMP_MEDIA_DIR = tempfile.mkdtemp()

# Función para borrar archivos después de 24 horas
def schedule_file_deletion(filepath, delay=86400):
    def delete_file():
        time.sleep(delay)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"Archivo eliminado: {filepath}")
        except Exception as e:
            print(f"Error al eliminar archivo: {e}")
    threading.Thread(target=delete_file).start()


# Endpoint para enviar un mensaje de texto normal
# Endpoint para enviar un mensaje de texto normal
@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        chat_room_id = data.get('chat_room_id')
        text_message = data.get('text_message')

        if not text_message:
            return jsonify({'status': 'error', 'message': 'No se proporcionó un mensaje de texto'}), 400

        # Crear nuevos user_id y chat_room_id si no se proporcionan
        user_id = user_id or f"user_{uuid.uuid4().hex}"
        chat_room_id = chat_room_id or f"room_{uuid.uuid4().hex}"

        # Clasificar la consulta para determinar el prompt adecuado
        prompt_key = gemini_chat_manager.classifier.classify_query(text_message, new_session=True)

        # Inicializar interacción con el modelo
        gemini_interact = GeminiInteract(
            prompt_key=prompt_key,
            user_id=user_id,
            chat_room_id=chat_room_id,
            max_history_messages=10
        )

        # Enviar el mensaje y obtener respuesta
        response = gemini_interact.send_single_message(message=text_message)

        # Retornar respuesta al cliente
        return jsonify({
            'status': 'success',
            'response': response.text if hasattr(response, 'text') else response,
            'prompt_used': prompt_key,
            'user_id': user_id,
            'chat_room_id': chat_room_id
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# Endpoint para enviar un mensaje con archivos multimedia
@app.route('/send_message_with_media', methods=['POST'])
def send_message_with_media():
    try:
        # Obtener parámetros del formulario
        user_id = request.form.get('user_id')
        chat_room_id = request.form.get('chat_room_id')
        text_message = request.form.get('text_message')

        if not text_message:
            return jsonify({'status': 'error', 'message': 'No se proporcionó un mensaje de texto'}), 400

        # Procesar archivos multimedia
        media_paths = []
        if 'media' in request.files:
            files = request.files.getlist('media')
            for file in files:
                # Crear nombre único para el archivo
                unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
                file_path = os.path.join(TEMP_MEDIA_DIR, unique_filename)
                file.save(file_path)  # Guardar archivo
                media_paths.append(file_path)
                schedule_file_deletion(file_path)  # Programar eliminación del archivo

        # Si no se proporcionan IDs, genera nuevos
        user_id = user_id or f"user_{uuid.uuid4().hex}"
        chat_room_id = chat_room_id or f"room_{uuid.uuid4().hex}"

        # Clasificar la consulta para determinar el prompt adecuado
        prompt_key = gemini_chat_manager.classifier.classify_query(text_message, new_session=True, user=user_id, chat_room=chat_room_id)

        # Inicializar instancia de GeminiInteract con los parámetros adecuados
        gemini_interact = GeminiInteract(
            prompt_key=prompt_key,
            user_id=user_id,
            chat_room_id=chat_room_id,
            max_history_messages=10
        )

        # Enviar mensaje con o sin multimedia
        if media_paths:
            response = gemini_interact.send_message_with_media(message=text_message, media_paths=media_paths)
        else:
            response = gemini_interact.send_single_message(message=text_message)

        # Retornar respuesta al cliente
        return jsonify({
            'status': 'success',
            'response': response.text if hasattr(response, 'text') else response,
            'prompt_used': prompt_key,
            'user_id': user_id,
            'chat_room_id': chat_room_id
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/get_chat_history', methods=['GET'])
def get_chat_history():
    try:
        user_id = request.args.get('user_id')
        chat_room_id = request.args.get('chat_room_id')

        if not user_id or not chat_room_id:
            return jsonify({'status': 'error', 'message': 'user_id y chat_room_id son requeridos'}), 400

        # Crear instancia del historial de chat
        chat_history_manager = ChatHistoryMongo(
            db_uri=MONGO_URI,
            db_name="Intelemi_translator",
            user_id=user_id,
            chat_room_id=chat_room_id
        )

        # Obtener historial formateado
        formatted_history = chat_history_manager.get_formatted_history()

        return jsonify({
            'status': 'success',
            'chat_history': formatted_history
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_user_chat_rooms', methods=['GET'])
def get_user_chat_rooms():
    try:
        user_id = request.args.get('user_id')  # user_id llega como string desde los argumentos

        if not user_id:
            return jsonify({'status': 'error', 'message': 'user_id es requerido'}), 400

        # Crear instancia del historial de chat
        chat_history_manager = ChatHistoryMongo(
            db_uri=MONGO_URI,
            db_name="Intelemi_translator",
            user_id=user_id.strip(),  # Eliminar espacios extra
            chat_room_id=None  # No necesario para este endpoint
        )

        # Obtener todas las salas de chat del usuario
        chat_rooms = chat_history_manager.get_all_chat_rooms_for_user()

        return jsonify({
            'status': 'success',
            'chat_rooms': chat_rooms
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
