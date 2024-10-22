import gradio as gr
from gemini_model.model import GeminiInteract

# Definir una instancia de GeminiInteract
gemini = GeminiInteract(prompt_key='profesional')

# Función para Gradio que interactúa con Gemini
def chat_with_gemini(message, history):
    response = gemini.send_single_message(message)
    history.append((message, response.text))
    return "", history

# Configurar el tema personalizado
theme = gr.themes.Default().set(
    body_background_fill="#f7f7f8",
    block_background_fill="#ffffff",
    block_border_width="0px",
    button_primary_background_fill="#10a37f",
    button_primary_text_color="#ffffff",
)

# Configurar la interfaz de Gradio
with gr.Blocks(theme=theme) as iface:
    gr.Markdown("# Gemini Chatbot")
    gr.Markdown("Interactúe con Gemini, un modelo de lenguaje avanzado.")
    
    chatbot = gr.Chatbot(height=400, show_label=False)
    msg = gr.Textbox(
        show_label=False,
        placeholder="Escribe tu mensaje aquí...",
        container=False
    )
    clear = gr.Button("Limpiar conversación")

    def clear_conversation():
        return None

    msg.submit(chat_with_gemini, [msg, chatbot], [msg, chatbot])
    clear.click(clear_conversation, outputs=[chatbot])

# Ejecutar la interfaz Gradio
if __name__ == "__main__":
    iface.launch()