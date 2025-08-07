import os
import gradio as gr

with gr.Blocks() as demo:
    gr.Markdown("✅ Gradio funktioniert!")

print("✅ Testscript erreicht .launch()")

demo.launch(server_port=int(os.environ.get("PORT", 7860)))
