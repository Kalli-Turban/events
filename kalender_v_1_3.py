# kalender_step1_v1_3.py
# Frontend (Gradio) – basiert auf "kalender_step1_v1_2_1.py"
# Änderungen in v1.3:
#  - show_location (vormals sichtbar) wird jetzt im Frontend ausgewertet: Ort wird nur angezeigt, wenn true
#  - Versions-Tag aktualisiert
#  - Rest wie v1.2.1 (published-Filter, Anmeldung/📧-Link, Drucken, Trennlinie, responsive Header/Actions)

import gradio as gr
from supabase import create_client
import os
from dotenv import load_dotenv

# === Version ===
__APP_VERSION__ = "Frontend v1.3"

# === Supabase Setup ===
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_ROLE")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Konstanten ===
EVENTS_PER_PAGE = 3
APP_TITLE = "Ein Service von Karl-Heinz -Kalli- Turban • Events & Termine der AfD in Berlin"
LOGO_PATH = "assets/kalli_logo.png"  # optional, wenn vorhanden

# === CSS (Header fix, responsive Actions, Print) ===
CUSTOM_CSS = """
#footer, footer { display:none !important; }

/* Toolbar-Buttons beim Bild verstecken (Download/Vollbild) */
button[aria-label="Herunterladen"],
button[aria-label="Vollbild"],
button[title="Herunterladen"],
button[title="Vollbild"],
button[aria-label="Fullscreen"],
button[title="Fullscreen"] { display:none !important; }

.kalli-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    border-radius: 12px;
    background: #f8fafc;
    overflow-x: visible;   /* statt auto */
    white-space: normal;   /* statt nowrap – Titel darf umbrechen */
}

/* Header-Scrollbar ausblenden */
.kalli-header::-webkit-scrollbar { display: none; }
.kalli-header { scrollbar-width: none; }

.kalli-title {
    font-weight: 700;
    font-size: 1.05rem;
    color: #000;
}

.kalli-subtitle {
    font-weight: 500;
    font-size: 0.9rem;
    opacity: 0.8;
}

/* Responsive Button-Zeile */
.kalli-actions { gap: 12px; flex-wrap: wrap; }
.kalli-actions .gr-button { flex: 1 1 200px; }

@media print {
  /* Alles verstecken ... */
  body * { visibility: hidden !important; }

  /* ... außer dem Eventbereich */
  #kalli-events, #kalli-events * {
    visibility: visible !important;
  }

  /* Eventbereich auf ganze Seite */
  #kalli-events {
    position: absolute !important;
    left: 0; top: 0; width: 100%;
    padding: 0 !important;
    background: #fff !important;
    width: 100% !important;
  }

  /* Header & Buttons ausblenden */
  .kalli-header, .gr-button { display: none !important; }
}
"""

# === Supabase Events laden ===
def load_events_db():
    try:
        response = (
            supabase
            .table("events")
            .select("*")
            .eq("published", True)
            .order("datum", desc=False)
            .execute()
        )
        if response.data:
            return response.data
        else:
            return [{
                "titel": "Keine veröffentlichten Termine vorhanden",
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
def format_event_card(event: dict) -> str:
    titel = event.get("titel", "") or ""
    datum = event.get("datum", "") or ""
    uhrzeit = event.get("uhrzeit", "") or ""
    dauer = event.get("dauer", "") or ""
    ort = event.get("ort", "") or ""
    kategorie = event.get("kategorie", "") or ""
    beschreibung = event.get("beschreibung", "") or ""
    link = event.get("link")
    pdf_url = event.get("pdf_url")

    # Neue Felder
    requires_registration = bool(event.get("requires_registration") or False)
    email_contact = (event.get("email_contact") or "").strip()

    # Ortssichtbarkeit auswerten (show_location)
    show_location = bool(event.get("show_location", True))

    # Badge/Zeile für Anmeldung
    registration_block = ""
    if requires_registration:
        if email_contact:
            email_address = email_contact
            registration_block = f"\n**📨 Anmeldung:** [{email_address}](mailto:{email_address})\n"
        else:
            registration_block = f"\n**📨 Anmeldung erforderlich**\n"

    link_block = f"🔗 [Mehr erfahren]({link})" if link else ""
    pdf_block = f"📄 [PDF anzeigen]({pdf_url})" if pdf_url else ""

    meta_line = f"🗓️ {datum}"
    if uhrzeit:
        meta_line += f" ⏰ {uhrzeit}"
    if dauer:
        meta_line += f" ({dauer})"

    # Ort nur anzeigen, wenn show_location true ist
    location_line = f"📍 {ort}" if (show_location and ort) else ""
    if kategorie:
        location_line = (location_line + " | " if location_line else "") + f"Kategorie: {kategorie}"

    md = f"""
### 📌 {titel}
{meta_line}  
{location_line}

{beschreibung}

{registration_block}
{link_block}{"  |  " if link_block and pdf_block else ""}{pdf_block}
""".strip("\n")

    return md

# === Anzeige mit Seitenblättern ===
def show_events_paginated(page=0):
    events = load_events_db()
    start = page * EVENTS_PER_PAGE
    end = start + EVENTS_PER_PAGE
    paginated = events[start:end]
    markdown = "\n\n---\n\n".join([format_event_card(e) for e in paginated])
    return markdown

# === GUI Aufbau ===
with gr.Blocks(css=CUSTOM_CSS, title=f"{APP_TITLE} · {__APP_VERSION__}") as demo:
    with gr.Row(elem_classes="kalli-header"):
        if os.path.exists(LOGO_PATH):
            gr.Image(LOGO_PATH, show_label=False, height=40, width=40, container=False)
            print(f"✅ Logo geladen: {LOGO_PATH}")
        else:
            print(f"⚠️ Logo nicht gefunden: {LOGO_PATH}")
        gr.HTML(f"<div><div class='kalli-title'>{APP_TITLE}</div>"
                f"<div class='kalli-subtitle'>{__APP_VERSION__}</div></div>")

    gr.Markdown("## 🗓️ Klartext-Kalender – Veranstaltungen")

    with gr.Row(elem_classes="kalli-actions"):
        back_btn = gr.Button("⬅️ Zurück")
        next_btn = gr.Button("Weiter ➡️")
        print_btn = gr.Button("🖨 Drucken")

    output_box = gr.Markdown(elem_id="kalli-events")
    current_page = gr.State(0)

    def go_back(page):
        return max(page - 1, 0), show_events_paginated(max(page - 1, 0))

    def go_next(page):
        return page + 1, show_events_paginated(page + 1)

    back_btn.click(fn=go_back, inputs=current_page, outputs=[current_page, output_box])
    next_btn.click(fn=go_next, inputs=current_page, outputs=[current_page, output_box])

    # Drucken (Browser-Print)
    print_btn.click(fn=None, js="window.print()")

    demo.load(fn=show_events_paginated, outputs=output_box)

if __name__ == "__main__":
    #demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
    demo.launch()