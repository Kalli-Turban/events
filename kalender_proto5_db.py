import gradio as gr
from supabase import create_client
import os
from dotenv import load_dotenv

# === Supabase Setup ===
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("✅ Supabase verbunden")
print(f"🔌 Verbunden mit Supabase: {SUPABASE_URL[:40]}...") if SUPABASE_KEY else print("❌ KEY fehlt!")

# === Events pro Seite ===öö
EVENTS_PER_PAGE = 3

# === Supabase Events laden ===
def load_events_db():
    try:
        response = supabase.table("events").select("*").order("datum", desc=False).execute()
        if response.data:
            return response.data
        else:
            return [{
                "titel": "Keine Daten",
                "datum": "", "uhrzeit": "", "dauer": "",
                "ort": "", "kategorie": "Hinweis", "link": "", "pdf_url": ""
            }]
    except Exception as e:
        return [{
            "titel": "Fehler beim DB-Zugriff",
            "datum": "", "uhrzeit": "", "dauer": "",
            "ort": "", "kategorie": "Fehler", "link": "",
            "pdf_url": f"{e}"
        }]

# === Formatierung eines einzelnen Events ===
def format_event_card(event):
    return f"""
### 📌 {event.get("titel", "")}
🗓️ {event.get("datum", "")} ⏰ {event.get("uhrzeit", "")} ({event.get("dauer", "")})  
📍 {event.get("ort", "")} | Kategorie: {event.get("kategorie", "")}  

{event.get("beschreibung", "")}

{"🔗 [Mehr erfahren](" + event["link"] + ")" if event.get("link") else ""}
{"📄 [PDF anzeigen](" + event["pdf_url"] + ")" if event.get("pdf_url") else ""}
"""

# === Anzeige logik mit Seitenblättern ===
def show_events_paginated(page=0):
    events = load_events_db()
    start = page * EVENTS_PER_PAGE
    end = start + EVENTS_PER_PAGE
    paginated = events[start:end]
    markdown = "\n---\n".join([format_event_card(e) for e in paginated])
    return markdown

# === GUI Aufbau ===
with gr.Blocks() as demo:
    gr.Markdown("## 🗓️ Klartext-Kalender – Veranstaltungen")

    with gr.Row():
        back_btn = gr.Button("⬅️ Zurück")
        next_btn = gr.Button("Weiter ➡️")

    output_box = gr.Markdown()
    current_page = gr.State(0)

    def go_back(page):
        return max(page - 1, 0), show_events_paginated(max(page - 1, 0))

    def go_next(page):
        return page + 1, show_events_paginated(page + 1)

    back_btn.click(fn=go_back, inputs=current_page, outputs=[current_page, output_box])
    next_btn.click(fn=go_next, inputs=current_page, outputs=[current_page, output_box])

    demo.load(fn=show_events_paginated, outputs=output_box)

if __name__ == "__main__":
    # demo.launch()

    print("✅ Kalli-Deploy erreicht demo.launch() mit Port:", os.environ.get("PORT", 7860))
    demo.launch(server_port=int(os.environ.get("PORT", 7860)))
    

