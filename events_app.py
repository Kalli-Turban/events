
"""
Events Frontend - Version 1.7.1 (Merged: Search + Stable Print)
Erstellt: 2025-08-15

© 2025 Karl-Heinz "Kalli" Turban & KalliGPT
Alle Rechte vorbehalten.
Lizenz: Privat / interne Nutzung

Dieser Merge vereint:
- 1.7.1-Features (Berlin-Zeitzone, gültiger Tipp-Zeitraum, Suche mit ilike, Clear-Button)
- Stabilen Druck-Mechanismus aus der funktionierenden Version (window.print())
- Konsistente Print-CSS und elem_id="kalli-events"
"""

import os
import math
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

import gradio as gr
from dotenv import load_dotenv
from supabase import create_client

__APP_VERSION__ = "Frontend v1.7.1 (Search+Print Merged)"

# ===== Supabase Setup =====
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_ROLE")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===== Konstanten =====
EVENTS_PER_PAGE = 6
APP_TITLE = "Ein Service von Karl-Heinz -Kalli- Turban • Events & Termine der AfD in Berlin"
LOGO_PATH = "assets/kalli_logo.png"  # optional

# ===== Zeit / Datum (Berlin) =====
def today_berlin() -> str:
    """Liefert das lokale Berlin-Datum als ISO-String (YYYY-MM-DD)."""
    try:
        return datetime.now(ZoneInfo("Europe/Berlin")).date().isoformat()
    except Exception:
        return date.today().isoformat()

# ===== CSS =====
CUSTOM_CSS = """
#footer, footer { display:none !important; }

/* Bild-Toolbar-Buttons ausblenden */
button[aria-label="Herunterladen"],
button[aria-label="Vollbild"],
button[title="Herunterladen"],
button[title="Vollbild"],
button[aria-label="Fullscreen"],
button[title="Fullscreen"] { display:none !important; }

.kalli-header {
  display:flex; align-items:center; gap:12px; padding:10px 12px;
  border-radius:12px; background:#f8fafc; overflow-x:visible; white-space:normal;
}
.kalli-header::-webkit-scrollbar { display:none; }
.kalli-header { scrollbar-width:none; }
.kalli-title { font-weight:700; font-size:1.05rem; color:#000; }
.kalli-subtitle { font-weight:500; font-size:0.9rem; opacity:0.8; }
.kalli-actions { gap:12px; flex-wrap:wrap; }
.kalli-actions .gr-button { flex: 1 1 200px; }

@media print {
  body * { visibility: hidden !important; }
  #kalli-events, #kalli-events * { visibility: visible !important; }
  #kalli-events {
    position: absolute !important; left: 0; top: 0; width: 100%;
    padding: 0 !important; background: #fff !important;
  }
  .kalli-header, .gr-button, #btn-clear { display: none !important; }
}
"""

# ===== Tipp-Bereich =====
def _public_url(res):
    if isinstance(res, str):
        return res
    if isinstance(res, dict):
        return res.get("publicUrl") or res.get("data", {}).get("publicUrl", "")
    return ""

def load_tipp(sb):
    today = today_berlin()
    try:
        data = (
            sb.table("site_news_tipp")
              .select("*")
              .eq("published", True)
              .lte("valid_from", today)
              .or_(f"valid_to.gte.{today},valid_to.is.null")
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

# ===== Rendering einer Event-Karte =====
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
    email_questions = (event.get("email_questions") or "").strip()

    registration_block = ""
    if requires_registration:
        if email_contact:
            registration_block = f"**✍️ Anmeldung:** [{email_contact}](mailto:{email_contact})"
        else:
            registration_block = f"**✍️ Anmeldung erforderlich**"

    meta_line = f"🗓️ {datum}"
    if uhrzeit:
        meta_line += f" ⏰ {uhrzeit}"
    if dauer:
        meta_line += f" ({dauer})"

    location_line = f"📍 {ort}" if (show_location and ort) else ""
    if kategorie:
        location_line = (location_line + " | " if location_line else "") + f"Kategorie: {kategorie}"

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

# ===== Suche + Pagination =====
def _tokens(q: str):
    return [t for t in re.split(r"\s+", (q or '').strip()) if t]

def search_page(query: str, page: int, show_all: bool, start_date_val: str | None):
    try:
        tbl = supabase.table("events").select("*", count="exact").eq("published", True)

        # Datumslogik: ab heute, außer 'Alle' ist an oder Startdatum gesetzt
        start = (start_date_val or "").strip() if start_date_val else None
        if not start and not show_all:
            start = today_berlin()
        if start:
            tbl = tbl.gte("datum", start[:10])

        for t in _tokens(query):
            ilike = f"%{t}%"
            tbl = tbl.or_("titel.ilike.{},kategorie.ilike.{},beschreibung.ilike.{},ort.ilike.{},status.ilike.{},team.ilike.{}".format(
                ilike, ilike, ilike, ilike, ilike, ilike
            ))

        tbl = tbl.order("datum", desc=False)
        start_idx = max(0, (max(1, page) - 1) * EVENTS_PER_PAGE)
        end_idx = start_idx + EVENTS_PER_PAGE - 1
        res = tbl.range(start_idx, end_idx).execute()
        data = res.data or []
        total = res.count or 0
        pages = max(1, math.ceil(total / EVENTS_PER_PAGE))
        page = min(max(1, page), pages)
        md = "\n\n---\n\n".join([format_event_card(e) for e in data]) if data else "Keine passenden Termine."
        return md, f"**{total} Treffer** · Seite {page}/{pages}", query, page
    except Exception as e:
        md = f"⚠️ Fehler bei der Suche: {e}\n\nBitte versuche es erneut oder setze die Filter zurück."
        return md, "**0 Treffer** · Seite 1/1", query, 1

def update_nav_from_info(info: str):
    m = re.search(r"Seite\s+(\d+)\s*/\s*(\d+)", info or "")
    if not m:
        return gr.update(visible=False), gr.update(visible=False)
    page, pages = int(m.group(1)), int(m.group(2))
    return gr.update(visible=page > 1), gr.update(visible=page < pages)

def _clamp_page_for(q, page, show_all, start_date_val):
    cq = supabase.table("events").select("id", count="exact").eq("published", True)
    start = (start_date_val or "").strip() if start_date_val else None
    if not start and not show_all:
        start = today_berlin()
    if start:
        cq = cq.gte("datum", start[:10])
    for t in _tokens(q):
        ilike = f"%{t}%"
        cq = cq.or_("titel.ilike.{},kategorie.ilike.{},beschreibung.ilike.{},ort.ilike.{},status.ilike.{},team.ilike.{}".format(
            ilike, ilike, ilike, ilike, ilike, ilike
        ))
    total = (cq.execute().count or 0)
    pages = max(1, math.ceil(total / EVENTS_PER_PAGE)) if total > 0 else 1
    return min(max(1, page), pages)

# ===== UI =====
with gr.Blocks(css=CUSTOM_CSS, title=f"{APP_TITLE} · {__APP_VERSION__}") as demo:
    # Header
    with gr.Row(elem_classes="kalli-header"): 
        if os.path.exists(LOGO_PATH):
            gr.Image(LOGO_PATH, show_label=False, height=40, width=40, container=False)
        gr.HTML(f"<div><div class='kalli-title'>{APP_TITLE}</div>"
                f"<div class='kalli-subtitle'>{__APP_VERSION__}</div></div>")

    # Tipp des Tages
    with gr.Row():
        tipp_md = gr.Markdown(visible=False)
        tipp_btn = gr.HTML(visible=False)
    gr.HTML('<div style="height:1px;background:#3a3a3a;margin:8px 0 14px;border-radius:1px;"></div>')

    gr.Markdown("## Veranstaltungen")

    # Filterleiste
    with gr.Row():
        suchfeld = gr.Textbox(label="🔎 Suche", placeholder="z. B. Stammtisch, Infostand … (min. 2 Zeichen)")
        clear_search = gr.Button("❌", elem_id="btn-clear", scale=0, min_width=48)
        show_all = gr.Checkbox(label="Alle Termine zeigen", value=False)
        start_date_inp = gr.DateTime(label="Ab Datum", include_time=False, type="string", info="leer = Standard (nur kommende)")

    with gr.Row(elem_classes="kalli-actions"):
        back_btn = gr.Button("⬅️ Zurück")
        next_btn = gr.Button("Weiter ➡️")
        print_btn = gr.Button("🖨 Drucken")

    # Stabiler Druck (wie in der funktionierenden Version)
    print_btn.click(fn=None, js="window.print()")

    page_info = gr.Markdown()
    output_box = gr.Markdown(elem_id="kalli-events")
    q_state = gr.State("")
    current_page = gr.State(1)

    # Handlers
    def do_search(q, show_all, start_date_val):
        qs = (q or "").strip()
        if qs and len(qs) < 2:
            md, info, _, _ = search_page("", 1, show_all, start_date_val)
            return md, info, "", 1
        md, info, _, _ = search_page(qs, 1, show_all, start_date_val)
        return md, info, qs, 1

    def go_back(q, page, show_all, start_date_val):
        p = _clamp_page_for(q, max(1, page-1), show_all, start_date_val)
        md, info, q2, p2 = search_page(q, p, show_all, start_date_val)
        return md, info, p2

    def go_next(q, page, show_all, start_date_val):
        p = _clamp_page_for(q, page+1, show_all, start_date_val)
        md, info, q2, p2 = search_page(q, p, show_all, start_date_val)
        return md, info, p2

    def clear_search_fn(show_all, start_date_val):
        md, info, _, _ = search_page("", 1, show_all, start_date_val)
        return md, info, "", 1, ""

    # Hooks
    suchfeld.change(fn=do_search, inputs=[suchfeld, show_all, start_date_inp],
                    outputs=[output_box, page_info, q_state, current_page]).then(
                        fn=update_nav_from_info, inputs=[page_info], outputs=[back_btn, next_btn]
                    )
    show_all.change(fn=do_search, inputs=[suchfeld, show_all, start_date_inp],
                    outputs=[output_box, page_info, q_state, current_page]).then(
                        fn=update_nav_from_info, inputs=[page_info], outputs=[back_btn, next_btn]
                    )
    start_date_inp.change(fn=do_search, inputs=[suchfeld, show_all, start_date_inp],
                          outputs=[output_box, page_info, q_state, current_page]).then(
                              fn=update_nav_from_info, inputs=[page_info], outputs=[back_btn, next_btn]
                          )

    back_btn.click(fn=go_back, inputs=[q_state, current_page, show_all, start_date_inp],
                   outputs=[output_box, page_info, current_page]).then(
                       fn=update_nav_from_info, inputs=[page_info], outputs=[back_btn, next_btn]
                   )
    next_btn.click(fn=go_next, inputs=[q_state, current_page, show_all, start_date_inp],
                   outputs=[output_box, page_info, current_page]).then(
                       fn=update_nav_from_info, inputs=[page_info], outputs=[back_btn, next_btn]
                   )
    clear_search.click(fn=clear_search_fn, inputs=[show_all, start_date_inp],
                       outputs=[output_box, page_info, suchfeld, current_page, q_state]).then(
                           fn=update_nav_from_info, inputs=[page_info], outputs=[back_btn, next_btn]
                       )

    # Initial Load
    demo.load(fn=do_search, inputs=[suchfeld, show_all, start_date_inp],
              outputs=[output_box, page_info, q_state, current_page])

    # Tipp laden
    def init_tipp():
        row = load_tipp(supabase)
        if not row:
            return gr.update(visible=False), gr.update(visible=False)
        md = f"""### {row['title']}

{row.get('body', '') or ''}"""
        btn = tipp_chip_html(row)
        return gr.update(value=md, visible=True), gr.update(value=btn, visible=bool(btn))

    demo.load(fn=init_tipp, outputs=[tipp_md, tipp_btn], queue=False)

if __name__ == "__main__":
   #demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
    demo.launch()