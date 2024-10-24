import gradio as gr
from chat_managment import GeminiChatManager
from typing import List, Dict, Tuple
import tempfile
import os

class GradioInterface:
    def __init__(self):
        self.chat_manager = GeminiChatManager()
        self.temp_dir = tempfile.mkdtemp()

    def _process_uploaded_files(self, files) -> List[str]:
        """Procesa los archivos subidos por Gradio"""
        if not files:
            return []
        
        # Los archivos de Gradio ya vienen como rutas
        return [file.name if hasattr(file, 'name') else str(file) for file in files]

    def chat_with_gemini(self, 
                        message: str, 
                        files: List[str], 
                        history: List[Tuple[str, str]]) -> Tuple[str, List[Tuple[str, str]], str]:
        """Procesa el mensaje y archivos, actualiza el historial"""
        try:
            # Procesar las rutas de los archivos
            media_paths = self._process_uploaded_files(files)
            
            # Procesar la solicitud
            response = self.chat_manager.process_request(
                text_message=message,
                media_paths=media_paths if media_paths else None
            )
            
            # Actualizar historial
            if response.status == 'success':
                history.append((message, response.response))
                return "", history, ""
            else:
                return "", history, f"Error: {response.error}"
                
        except Exception as e:
            return "", history, f"Error inesperado: {str(e)}"

    def clear_conversation(self):
        """Limpia la conversación y los recursos"""
        self.chat_manager.cleanup()
        return None, None

    def create_interface(self):
        """Crea y configura la interfaz de Gradio"""
        theme = gr.themes.Default().set(
            body_background_fill="#f7f7f8",
            block_background_fill="#ffffff",
            block_border_width="0px",
            button_primary_background_fill="#10a37f",
            button_primary_text_color="#ffffff",
        )

        with gr.Blocks(theme=theme) as iface:
            gr.Markdown("# Gemini AI Assistant")
            gr.Markdown("Interactúe con Gemini: envíe mensajes, imágenes o videos.")
            
            with gr.Row():
                with gr.Column(scale=4):
                    chatbot = gr.Chatbot(
                        height=400,
                        show_label=False,
                        container=True
                    )
                    
                    with gr.Row():
                        with gr.Column(scale=8):
                            msg = gr.Textbox(
                                show_label=False,
                                placeholder="Escribe tu mensaje aquí...",
                                container=False
                            )
                        with gr.Column(scale=2):
                            file_output = gr.File(
                                file_count="multiple",
                                label="Archivos subidos"
                            )
                    
                    with gr.Row():
                        clear = gr.Button("🗑️ Limpiar conversación")
                        error_box = gr.Textbox(
                            show_label=False,
                            visible=True,
                            interactive=False
                        )

            # Configurar eventos
            msg.submit(
                self.chat_with_gemini,
                inputs=[msg, file_output, chatbot],
                outputs=[msg, chatbot, error_box]
            )
            
            clear.click(
                self.clear_conversation,
                outputs=[chatbot, error_box]
            )

        return iface

def main():
    interface = GradioInterface()
    iface = interface.create_interface()
    iface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True
    )

if __name__ == "__main__":
    main()