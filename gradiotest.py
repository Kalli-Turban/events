import gradio as gr
import os

def ping():
    return "✅ Render lebt!"

demo = gr.Interface(fn=ping, inputs=[], outputs="text")

print("✅ Kalli: Starte Gradio auf PORT", os.environ.get("PORT", 7860))

demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
