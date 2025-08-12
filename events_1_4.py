# events_1_2.py
# Ein-Datei-Frontend (Gradio)
# Fix: gr.Date -> gr.DateTime (Gradio v5.x)
# - Date-Picker jetzt: gr.DateTime(include_time=False, type="string")
# - Startdatum-Handling vereinfacht (String)
#
# --- Kurzüberblick ---
# Dieses Script zeigt veröffentlichte Events aus Supabase mit optionalem Startdatum-Filter.
# Standard: ab heutigem Datum; „Alle Termine“ hebt die Beschränkung auf.
# Frontend via Gradio: Paginierung, Druck-Button, responsiver Header.
# Datenschutz: Ort wird nur angezeigt, wenn show_location=True.
# Kontakt: optionaler mailto:-Link bei requires_registration.

import os
from datetime import date
import gradio as gr
from dotenv import load_dotenv
from supabase import create_client

# ===== Version =====
__APP_VERSION__ = "Frontend v1.2 Final (fix)"

# ===== Supabase Setup =====
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
# Sicherer Default: ANON; SERVICE_ROLE nur falls bewusst gesetzt (nicht empfohlen im Frontend)
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_ROLE")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===== Konstanten =====
EVENTS_PER_PAGE = 3
APP_TITLE = "Ein Service von Karl-Heinz -Kalli- Turban • Events & Termine der AfD in Berlin"
LOGO_PATH = "assets/kalli_logo.png"  # optional

# ===== CSS =====
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
    overflow-x: visible;   /* kein Scrollen */
    white-space: normal;   /* Titel darf umbrechen */
}

/* Header-Scrollbar ausblenden */
.kalli-header::-webkit-scrollbar { display: none; }
.kalli-header { scrollbar-width: none; }

.kalli-title { font-weight: 700; font-size: 1.05rem; color: #000; }
.kalli-subtitle { font-weight: 500; font-size: 0.9rem; opacity: 0.8; }

/* Responsive Button-Zeile */
.kalli-actions { gap: 12px; flex-wrap: wrap; }
.kalli-actions .gr-button { flex: 1 1 200px; }

@media print {
  /* Alles verstecken ... */
  body * { visibility: hidden !important; }

  /* ... außer dem Eventbereich */
  #kalli-events, #kalli-events * { visibility: visible !important; }

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

# ===== DB-Zugriff =====
def load_events_db(start_date: str | None = None):
    """Lädt veröffentlichte Events; optional ab einem Startdatum (YYYY-MM-DD)."""
    try:
        # Basis-Query: nur veröffentlichte Events (published=true)
        q = (
            supabase
            .table("events")
            .select("*")
            .eq("published", True)
        )
        # Optional: ab Startdatum filtern
        if start_date:
            q = q.gte("datum", start_date)
        res = q.order("datum", desc=False).execute()  # aufsteigend nach Datum
        data = res.data or []
        if data:
            return data
        return [{
            "titel": "Keine passenden Termine",
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

# ===== Rendering einer Event-Karte =====

# ===== Tagestipp (unter dem Header) =====
def _public_url(res):
    # supabase-python kann je nach Version String oder Dict liefern
    if isinstance(res, str):
        return res
    if isinstance(res, dict):
        return res.get("publicUrl") or res.get("data", {}).get("publicUrl", "")
    return ""

def load_tipp(sb):
    """Liest den aktuellsten veröffentlichten Tipp (RLS filtert gültige)."""
    try:
        data = (
            sb.table("site_news_tipp")
              .select("*")
              .eq("published", True)
              .order("valid_from", desc=True)
              .order("created_at", desc=True)
              .limit(1)
              .execute()
        ).data
        return data[0] if data else None
    except Exception:
        return None

def resolve_cta_url(row):
    kind = (row.get("cta_kind") or "").lower()
    if kind == "external":
        return row.get("cta_url") or ""
    if kind == "storage":
        b, p = row.get("storage_bucket"), row.get("storage_path")
        if not (b and p):
            return ""
        return _public_url(supabase.storage.from_(b).get_public_url(p))
    return ""

def tipp_chip_html(row):
    if not row:
        return ""
    url = resolve_cta_url(row)
    if not url:
        return ""
    label = (row.get("cta_label") or "Mehr lesen") + " ↗"
    return (
        f'<a href="{url}" target="_blank" rel="noopener" '
        'style="display:inline-block;padding:8px 12px;border:1px solid #888;'
        'border-radius:999px;text-decoration:none;font-weight:600;">'
        f'💡 {label}</a>'
    )

def init_tipp():
    row = load_tipp(supabase)
    if not row:
        return gr.update(visible=False), gr.update(visible=False)
    md = f"""### {row['title']}

{row.get('body', '') or ''}"""
    btn = tipp_chip_html(row)
    return gr.update(value=md, visible=True), gr.update(value=btn, visible=bool(btn))

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

    requires_registration = bool(event.get("requires_registration") or False)
    email_contact = (event.get("email_contact") or "").strip()
    show_location = bool(event.get("show_location", True))

    # Fragen-Mail pro Event oder Fallback aus .env
    #email_questions = (event.get("email_questions") or os.getenv("DEFAULT_EVENT_QUESTIONS_EMAIL") or "").strip()

# NEU (ohne Fallback)
    email_questions = (event.get("email_questions") or "").strip()

    # Anmeldung
    registration_block = ""
    if requires_registration:
        if email_contact:
            registration_block = f"**✍️ Anmeldung:** [{email_contact}](mailto:{email_contact})"
        else:
            registration_block = f"**✍️ Anmeldung erforderlich**"

    # Metazeilen
    meta_line = f"🗓️ {datum}"
    if uhrzeit:
        meta_line += f" ⏰ {uhrzeit}"
    if dauer:
        meta_line += f" ({dauer})"

    # Ort nur anzeigen, wenn show_location true
    location_line = f"📍 {ort}" if (show_location and ort) else ""
    if kategorie:
        location_line = (location_line + " | " if location_line else "") + f"Kategorie: {kategorie}"

    # Footer-Parts (Links + Kontakt)
    link_block = f"🔗 [Mehr erfahren]({link})" if link else ""
    pdf_block = f"📄 [PDF anzeigen]({pdf_url})" if pdf_url else ""

    footer_parts = []
    if registration_block:
        footer_parts.append(registration_block)
    if email_questions:
        footer_parts.append(f"📧 Fragen: [{email_questions}](mailto:{email_questions})")
    if link_block:
        footer_parts.append(link_block)
    if pdf_block:
        footer_parts.append(pdf_block)

    footer_line = "  |  ".join(footer_parts) if footer_parts else ""

    md = f"""
### 📌 {titel}
{meta_line}  
{location_line}

{beschreibung}

{footer_line}
""".strip("\n")
    return md
def show_events_paginated(page=0, show_all=False, start_date_val: str | None = None):
    # Priorität: Startdatum > Alle > Standard (heute)
    start = (start_date_val or "").strip() if start_date_val else None
    if not start and not show_all:
        start = date.today().isoformat()

    events = load_events_db(start)
    # Pagination (3 pro Seite)
    start_idx = page * EVENTS_PER_PAGE
    end_idx = start_idx + EVENTS_PER_PAGE
    paginated = events[start_idx:end_idx]
    markdown = "\n\n---\n\n".join([format_event_card(e) for e in paginated])
    return markdown

# ===== UI =====
with gr.Blocks(css=CUSTOM_CSS, title=f"{APP_TITLE} · {__APP_VERSION__}") as demo:
    # Header
    with gr.Row(elem_classes="kalli-header"):
        if os.path.exists(LOGO_PATH):
            gr.Image(LOGO_PATH, show_label=False, height=40, width=40, container=False)
            print(f"✅ Logo geladen: {LOGO_PATH}")
        else:
            print(f"⚠️ Logo nicht gefunden: {LOGO_PATH}")
        gr.HTML(f"<div><div class='kalli-title'>{APP_TITLE}</div>"
                f"<div class='kalli-subtitle'>{__APP_VERSION__}</div></div>")

    # Tipp-Block unter dem Header
    with gr.Row():
        tipp_md = gr.Markdown(visible=False)
        tipp_btn = gr.HTML(visible=False)

    tipp_div = gr.HTML('<div style="height:1px;background:#3a3a3a;margin:8px 0 14px;border-radius:1px;"></div>')

    gr.Markdown("## Veranstaltungen")

    # Filterleiste – entweder alle Termine zeigen oder per Startdatum einschränken
    with gr.Row():
        show_all = gr.Checkbox(label="Alle Termine zeigen", value=False)
        # Gradio v5: Date-Picker ist gr.DateTime; nur Datum, als String
        start_date_inp = gr.DateTime(label="Ab Datum", include_time=False, type="string", info="leer = Standard (nur kommende)")

    with gr.Row(elem_classes="kalli-actions"):
        back_btn = gr.Button("⬅️ Zurück")
        next_btn = gr.Button("Weiter ➡️")
        print_btn = gr.Button("🖨 Drucken")

    output_box = gr.Markdown(elem_id="kalli-events")
    current_page = gr.State(0)

    def go_back(page, show_all, start_date_val):
        new_page = max(page - 1, 0)
        return new_page, show_events_paginated(new_page, show_all, start_date_val)

    def go_next(page, show_all, start_date_val):
        new_page = page + 1
        return new_page, show_events_paginated(new_page, show_all, start_date_val)

    back_btn.click(fn=go_back, inputs=[current_page, show_all, start_date_inp], outputs=[current_page, output_box])
    next_btn.click(fn=go_next, inputs=[current_page, show_all, start_date_inp], outputs=[current_page, output_box])

    # Drucken (Browser)
    print_btn.click(fn=None, js="window.print()")

    # Filter-Änderungen triggern Neurender
    show_all.change(fn=show_events_paginated, inputs=[current_page, show_all, start_date_inp], outputs=output_box)
    start_date_inp.change(fn=show_events_paginated, inputs=[current_page, show_all, start_date_inp], outputs=output_box)

    demo.load(fn=init_tipp, outputs=[tipp_md, tipp_btn], queue=False)

    demo.load(fn=show_events_paginated, inputs=[current_page, show_all, start_date_inp], outputs=output_box)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
    #demo.launch()
