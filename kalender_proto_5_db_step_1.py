import gradio as gr
from supabase import create_client
import os
from dotenv import load_dotenv

# === Supabase Setup ===
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE")  # read-only im Frontend: nutzt nur SELECT
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("✅ Supabase verbunden")
print(f"🔌 Verbunden mit Supabase: {SUPABASE_URL[:40]}...") if SUPABASE_URL else print("❌ SUPABASE_URL fehlt!")

# === Konstante ===
EVENTS_PER_PAGE = 3
APP_TITLE = "Ein Service von Karl-Heinz -Kalli- Turban • Events & Termine der AfD in Berlin"
LOGO_PATH = "assets/kalli_logo.png"  # optional, wenn vorhanden

# === Dezentes CSS (nur Header + Footer ausblenden) ===
CUSTOM_CSS = """
#footer, footer { display:none !important; }
.kalli-header { display:flex; align-items:center; gap:12px; padding:10px 12px; border-radius:12px; background:#f8fafc; }
.kalli-title { 
    font-weight:700; 
    font-size:1.1rem; 
    color:#000;  /* Schwarze Schrift auf hellem Hintergrund */
}
"""



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

# === Formatierung eines einzelnen Events (wie gehabt) ===

def format_event_card(event):
    return f"""
### 📌 {event.get("titel", "")}
🗓️ {event.get("datum", "")} ⏰ {event.get("uhrzeit", "")} ({event.get("dauer", "")})  
📍 {event.get("ort", "")} | Kategorie: {event.get("kategorie", "")}  

{event.get("beschreibung", "")}

{"🔗 [Mehr erfahren](" + event["link"] + ")" if event.get("link") else ""}
{"📄 [PDF anzeigen](" + event["pdf_url"] + ")" if event.get("pdf_url") else ""}
"""

# === Anzeige mit Seitenblättern (wie gehabt) ===

def show_events_paginated(page=0):
    events = load_events_db()
    start = page * EVENTS_PER_PAGE
    end = start + EVENTS_PER_PAGE
    paginated = events[start:end]
    markdown = "\n---\n".join([format_event_card(e) for e in paginated])
    return markdown

# === GUI Aufbau (nur Header ergänzt) ===
with gr.Blocks(css=CUSTOM_CSS, title=APP_TITLE) as demo:
    # Header (neu)
    with gr.Row(elem_classes="kalli-header"):
        if os.path.exists(LOGO_PATH):
            gr.Image(LOGO_PATH, show_label=False, height=40, width=40, container=False)
        gr.Markdown(f"<div class='kalli-title'>{APP_TITLE}</div>")

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
    demo.launch()
