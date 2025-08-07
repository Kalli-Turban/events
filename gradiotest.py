import gradio as gr
import os

def ping():
    return "✅ Render lebt!"

app = gr.Interface(fn=ping, inputs=[], outputs="text")

print("✅ Kalli: Starte Gradio auf PORT", os.environ.get("PORT", 7860))

app.launch(server_port=int(os.environ.get("PORT", 7860)), share=False, debug=True)
