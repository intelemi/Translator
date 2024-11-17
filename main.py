from flask import Flask, request, jsonify
from gemini_model.chat_managment import GeminiChatManager

# Crear instancia de Flask
app = Flask(__name__)

# Crear instancia del chat manager
gemini_chat_manager = GeminiChatManager(max_history_messages=10)

# Endpoint para enviar un mensaje de texto normal
@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        data = request.get_json()
        text_message = data.get('text_message')
        if not text_message:
            return jsonify({'status': 'error', 'message': 'No se proporcionó un mensaje de texto'}), 400

        response = gemini_chat_manager.process_request(text_message=text_message)
        return jsonify({'status': response.status, 'response': response.response, 'prompt_used': response.prompt_used})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Endpoint para enviar un mensaje con archivos multimedia
@app.route('/send_message_with_media', methods=['POST'])
def send_message_with_media():
    try:
        data = request.get_json()
        text_message = data.get('text_message')
        media_paths = data.get('media_paths', [])
        if not text_message:
            return jsonify({'status': 'error', 'message': 'No se proporcionó un mensaje de texto'}), 400

        response = gemini_chat_manager.process_request(text_message=text_message, media_paths=media_paths)
        return jsonify({'status': response.status, 'response': response.response, 'prompt_used': response.prompt_used})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Endpoint para obtener el historial de la conversación
@app.route('/get_chat_history', methods=['GET'])
def get_chat_history():
    try:
        history = gemini_chat_manager.get_chat_history()
        if not history:
            return jsonify({'status': 'error', 'message': 'No hay historial disponible'}), 404

        formatted_history = []
        for msg in history.messages:
            formatted_message = {
                'role': 'user' if msg['role'] == 'user' else 'assistant',
                'content': msg['parts']
            }
            formatted_history.append(formatted_message)

        return jsonify({'status': 'success', 'history': formatted_history})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Ejecutar la aplicación Flask
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
