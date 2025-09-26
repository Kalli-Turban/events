# ============================================================
#  Events-Frontend
#  V2.4 (2025-08-24) neues Feld für Zielgruppe event_level mit CSS 
#- v2.3 (2025-08-22) [KI+Kalli]
#    • CSS komplett ins Hauptscript zurückgeführt
#    • Logo responsive & skalierbar
#    • Header-Farbe auf Himmelblau geändert
#    • Ticker-Platzhalter eingebaut
#    • Finalisierung und Markierung als stabile Version
#  Changelog:
#   - v2.2 (2025-08-19) [KI+Kalli]:
#       • Druck-Button repariert:
#         - Warnung "too many outputs" behoben (fn=lambda: None statt "ping")
#         - Event-Kette mit .then(js=...) eingebaut
#         - Fallback: direkter JS-Listener (DOM), da Gradio-JS teils verschluckt
#       • Kommentarblock "Druck-Workaround" hinzugefügt
#
#   - v2.1 (2025-08-18) [KI+Kalli]:
#       • Code refaktorisiert in Blöcke
#       • Deployment/Local-Test Switch (demo.launch)
#
#  Autoren: KI + Kalli
# ============================================================

# =============================
# BLOCK 1 — Header & Setup
# =============================

# ----- Imports & Setup -----
import os
import math
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

import gradio as gr
from dotenv import load_dotenv
from supabase import create_client

# ----- App Version -----
__APP_VERSION__ = "Frontend v2.4 (mit Zielgruppe)"

# ----- Supabase Setup -----
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_ROLE")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ----- Konstanten -----
EVENTS_PER_PAGE = 6
APP_TITLE = "Ein Service von Karl-Heinz -Kalli- Turban • Events & Termine der Alternative für Deutschland"
LOGO_PATH = "assets/logo_160_80.png"

# ----- Zeit / Datum -----
def today_berlin() -> str:
    try:
        return datetime.now(ZoneInfo("Europe/Berlin")).date().isoformat()
    except Exception:
        return date.today().isoformat()

# ----- CSS -----
CUSTOM_CSS = """
#footer, footer { display:none !important; }
button[aria-label="Herunterladen"], button[aria-label="Vollbild"],
button[title="Herunterladen"], button[title="Vollbild"],
button[aria-label="Fullscreen"], button[title="Fullscreen"] { display:none !important; }

.kalli-header { display:flex; align-items:center; gap:12px; padding:10px 12px;
  border-radius:12px; background:#87CEEB; overflow-x:visible; white-space:normal; }
.kalli-header::-webkit-scrollbar { display:none; }
.kalli-header { scrollbar-width:none; }
.kalli-title { font-weight:700; font-size:1.05rem; color:#000; }
.kalli-subtitle { font-weight:500; font-size:0.9rem; opacity:0.8; }
.kalli-actions { gap:12px; flex-wrap:wrap; }
.kalli-actions .gr-button { flex: 1 1 200px; }
.logo img { width:160px; height:80px; border-radius:10%; object-fit:cover; }
.kalli-event-level { font-weight: bold; color: #555; margin-bottom: 6px; }

@media print {
  body * { visibility: hidden !important; }
  #kalli-events, #kalli-events * { visibility: visible !important; }
  #kalli-events { position: absolute !important; left: 0; top: 0; width: 100%;
    padding: 0 !important; background: #fff !important; }

  /* Filterleiste, Header, Aktionen komplett aus dem Layout entfernen */
  .kalli-header, .kalli-actions, #filterbar { display: none !important; }
  .kalli-header *, .kalli-actions *, #filterbar * { display: none !important; }

  /* Sicherheitsnetz gegen Tooltips/Popover/Portals */
  [role="tooltip"], [data-testid="tooltip"], .tooltip, .popover { display: none !important; }
  #btn-clear { display: none !important; }
}
"""

# =============================
# BLOCK 1a — ICS-Helper
# =============================

# slugify(text): hübsche Dateinamen (ASCII, Bindestriche).
#ics_escape(text): RFC5545-Escapes für Summary/Location/Des#cription/URL.
#to_utc_z(iso_ts): ISO → YYYYMMDDTHHMMSSZ in UTC.
#derive_times_from_event(ev): robustes Start/Ende aus start_iso/end_iso oder aus datum/uhrzeit/dauer (Berlin-TZ, Default 120 min).
#build_ics_event(ev, prodid=...): baut die .ics (ein VEVENT).
#ics_filename_for_event(ev): <slug>_<YYYY-MM-DD>.ics
# Diese Helfer bauen eine .ics (ein einzelnes VEVENT) für ein Event-Dict.
# Sie sind bewusst unabhängig vom UI (Markdown/Buttons/Route), damit wir sie
# überall wiederverwendbar nutzen können (HTTP-Route, Gradio-DownloadButton, Batch-Export).

from datetime import timedelta  # Ergänzung lokal, damit globaler Import unberührt bleibt
import unicodedata

def slugify(text: str) -> str:
    """
    ASCII-Slug für Dateinamen/UID-Bestandteile.
    z. B. "Bürgerdialog Neue Mitte" -> "burgerdialog-neue-mitte"
    """
    s = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "event"

def ics_escape(text: str) -> str:
    """RFC5545-Escapes für Kommata, Semikolon, Backslash und Zeilenumbrüche."""
    return (text or "").replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")

def to_utc_z(iso_ts: str) -> str:
    """ISO-String (mit/ohne TZ) -> UTC im Format YYYYMMDDTHHMMSSZ."""
    dt = datetime.fromisoformat(iso_ts)
    if dt.tzinfo is None:
        dt = dt.astimezone()  # lokale TZ annehmen (System)
    return dt.astimezone(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")

def derive_times_from_event(ev: dict) -> tuple[bool, str, str]:
    """
    Leitet Start/Ende her (mit robusten Fallbacks).

    Rückgabe:
      (all_day, start_repr, end_repr)
      -> all_day == True  => reprs sind 'YYYY-MM-DD'
      -> all_day == False => reprs sind ISO-Timestamps

    Logik:
      1) Wenn 'start_iso'/'end_iso' im Datensatz: nimm die direkt.
      2) Sonst aus 'datum' + 'uhrzeit' + 'dauer' heuristisch (Berlin TZ).
      3) Wenn keine Uhrzeit da ist: behandle als Ganztag.
    """
    start_iso = ev.get("start_iso")
    end_iso   = ev.get("end_iso")
    if start_iso and end_iso:
        return False, start_iso, end_iso

    datum = (ev.get("datum") or "")[:10]  # 'YYYY-MM-DD'
    uhr   = (ev.get("uhrzeit") or "").strip()

    if datum and uhr:
        # Uhrzeit parsen (best effort)
        try:
            hh, mm = [int(x) for x in uhr.split(":")[:2]]
        except Exception:
            hh, mm = 9, 0
        start_dt = datetime(
            int(datum[:4]), int(datum[5:7]), int(datum[8:10]),
            hh, mm, tzinfo=ZoneInfo("Europe/Berlin")
        )
        # Dauer erkennen (z. B. "90 min" oder "2h"); Default 120min
        dur = (ev.get("dauer") or "").strip().lower()
        mins = 120
        m = re.search(r"(\d+)\s*(min|minute|minuten)", dur)
        h = re.search(r"(\d+)\s*(h|std|stunde|stunden)", dur)
        if h:
            mins = int(h.group(1)) * 60
        elif m:
            mins = int(m.group(1))
        end_dt = start_dt + timedelta(minutes=mins)
        return False, start_dt.isoformat(), end_dt.isoformat()

    # Fallback: Ganztag des Datums
    return True, datum, datum


def build_ics_event(ev: dict, *, prodid: str = "-//Kalli Events//DE") -> bytes:
    """
    Baut eine minimal saubere ICS (ein VEVENT) aus einem Event-Dict.

    Erwartete Felder (so weit vorhanden):
      - id (str|int)
      - titel / title
      - datum (YYYY-MM-DD)
      - uhrzeit (optional, HH:MM)
      - dauer (optional, z. B. "90 min", "2h")
      - ort, beschreibung, link/pdf_url (optional)
      - optional: start_iso, end_iso (ISO 8601, mit/ohne TZ)

    Rückgabe: bytes der .ics (UTF-8, CRLF-Zeilenenden).
    """
    uid = f"{ev.get('id', 'unknown')}@kalli-events"
    now = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")

    all_day, start_repr, end_repr = derive_times_from_event(ev)

    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{prodid}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
    ]

    if all_day or (len(start_repr) == 10 and len(end_repr) == 10):
        # Hinweis: RFC-konform wäre DTEND = Folgetag; das implementieren wir bei Bedarf.
        lines += [
            f"DTSTART;VALUE=DATE:{start_repr.replace('-', '')}",
            f"DTEND;VALUE=DATE:{end_repr.replace('-', '')}",
        ]
    else:
        lines += [
            f"DTSTART:{to_utc_z(start_repr)}",
            f"DTEND:{to_utc_z(end_repr)}",
        ]

    summary  = ev.get("titel") or ev.get("title") or "Termin"
    location = ev.get("ort") or ""
    desc     = ev.get("beschreibung") or ""
    url      = ev.get("link") or ev.get("pdf_url") or ""

    lines += [
        f"SUMMARY:{ics_escape(summary)}",
        f"LOCATION:{ics_escape(location)}",
        f"DESCRIPTION:{ics_escape(desc)}",
        f"URL:{ics_escape(url)}",
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ]
    return "\r\n".join(lines).encode("utf-8")

def ics_filename_for_event(ev: dict) -> str:
    """Hübscher Dateiname: <slug>_<YYYY-MM-DD>.ics"""
    title = ev.get("titel") or ev.get("title") or "event"
    date_ = (ev.get("datum") or "")[:10]
    return f"{slugify(title)}_{date_}.ics"

# =============================
# BLOCK 2 — Tipp-Bereich & Event-Card Rendering
# =============================

# ----- Tipp-Helpers -----
def _public_url(res):
    if isinstance(res, str):
        return res
    if isinstance(res, dict):
        return res.get("publicUrl") or res.get("data", {}).get("publicUrl", "")
    return ""

# ----- Tipp laden -----
def load_tipp(sb):
    today = today_berlin()
    try:
        data = (sb.table("site_news_tipp").select("*")
                .eq("published", True)
                .lte("valid_from", today)
                .or_(f"valid_to.gte.{today},valid_to.is.null")
                .order("valid_from", desc=True)
                .order("created_at", desc=True)
                .limit(1)
                .execute()).data
        return data[0] if data else None
    except Exception:
        return None

# ----- CTA URL Resolver -----
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

# ----- Tipp Chip HTML -----
def tipp_chip_html(row):
    if not row:
        return ""
    url = resolve_cta_url(row)
    if not url:
        return ""
    label = (row.get("cta_label") or "Mehr Infos") + " ↗"
    return f'<a href="{url}" target="_blank" rel="noopener" style="display:inline-block;padding:8px 12px;border:1px solid #888;border-radius:999px;text-decoration:none;font-weight:600;">💡 {label}</a>'

# ----- Event-Karte Rendering -----

def format_event_card(event: dict) -> str:
    titel = event.get("titel", "") or ""
    datum = event.get("datum", "") or ""
    uhrzeit = event.get("uhrzeit", "") or ""
    dauer = event.get("dauer", "") or ""
    ort = event.get("ort", "") or ""
    kategorie = event.get("kategorie", "") or ""
    beschreibung = event.get("beschreibung", "") or ""
    level = (event.get("event_level") or "").strip()
    #level_line = f"🟢 Offenes Event? *{level}*" if level else ""
    level_html = f'<div class="kalli-event-level">🟢 Offenes Event? <strong>{level}</strong></div>' if level else ""
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
{level_html}
{meta_line}  

{location_line}

{beschreibung}

{footer_line}
""".strip("\n")
    return md

#BASE_PATH = ""  # ggf. später "/events" o.ä.
#def format_event_card(e: dict) -> str:
#    md = ""  # ...dein bisheriges Karten-Markdown (Titel, Zeit, Ort, Links)...
#    ics_href = f"{BASE_PATH}/ics/{e['id']}"
#    # Klickbarer „Button“ via Link:
#    md += (
#        "\n\n"
#        f'<a href="{ics_href}" download '
#        'style="display:inline-block;padding:8px 12px;border-radius:10px;'
#        'background:#1f6feb;color:#fff;text-decoration:none;font-weight:600;">'
#        '🗓️ ICS herunterladen</a>'
#    )
#    # Optional: ID sichtbar (nur zu Debug-Zwecken)
#    md += f"\n\n<small>ID: <code>{e['id']}</code></small>"
#    return md



# =============================
# BLOCK 3 — DB Suche & Pagination
# =============================

# ----- Tokenizer -----
def _tokens(q: str):
    return [t for t in re.split(r"\s+", (q or '').strip()) if t]

# ----- Suche Seite -----
def search_page(query: str, page: int, show_all: bool, start_date_val: str | None):
    try:
        tbl = supabase.table("events").select("*", count="exact").eq("published", True)
        start = (start_date_val or "").strip() if start_date_val else None
        if not start and not show_all:
            start = today_berlin()
        if start:
            tbl = tbl.gte("datum", start[:10])
        for t in _tokens(query):
            ilike = f"%{t}%"
            tbl = tbl.or_("titel.ilike.{},kategorie.ilike.{},beschreibung.ilike.{},ort.ilike.{},status.ilike.{},team.ilike.{}".format(ilike, ilike, ilike, ilike, ilike, ilike))
        tbl = tbl.order("datum", desc=False)
        start_idx = max(0, (max(1, page) - 1) * EVENTS_PER_PAGE)
        end_idx = start_idx + EVENTS_PER_PAGE - 1
        # → sagt: nimm die Tabelle events, hol alle Spalten, zähl mit (count="exact") und filtere nur published = True.
        res = tbl.range(start_idx, end_idx).execute()
        # >>> IDs der aktuellen Seite extrahieren
        ids = [ev["id"] for ev in (res.data or [])]
        print("Aktuelle Event-IDs:", ids)   # Debug ins Terminal
        # später geben wir diese IDs zusätzlich zurück (event_ids_state)
        data, total = res.data or [], res.count or 0
        pages = max(1, math.ceil(total / EVENTS_PER_PAGE))
        page = min(max(1, page), pages)
        md = "\n\n---\n\n".join([format_event_card(e) for e in data]) if data else "Keine passenden Termine."
        return md, f"**{total} Treffer** · Seite {page}/{pages}", query, page
    except Exception as e:
        return f"⚠️ Fehler bei der Suche: {e}\n\nBitte versuche es erneut oder setze die Filter zurück.", "**0 Treffer** · Seite 1/1", query, 1

# ----- Navigation Update -----
def update_nav_from_info(info: str):
    m = re.search(r"Seite\s+(\d+)\s*/\s*(\d+)", info or "")
    if not m:
        return gr.update(visible=False), gr.update(visible=False)
    page, pages = int(m.group(1)), int(m.group(2))
    return gr.update(visible=page > 1), gr.update(visible=page < pages)

# ----- Clamp Page -----
def _clamp_page_for(q, page, show_all, start_date_val):
    cq = supabase.table("events").select("id", count="exact").eq("published", True)
    start = (start_date_val or "").strip() if start_date_val else None
    if not start and not show_all:
        start = today_berlin()
    if start:
        cq = cq.gte("datum", start[:10])
    for t in _tokens(q):
        ilike = f"%{t}%"
        cq = cq.or_("titel.ilike.{},kategorie.ilike.{},beschreibung.ilike.{},ort.ilike.{},status.ilike.{},team.ilike.{}".format(ilike, ilike, ilike, ilike, ilike, ilike))
    total = (cq.execute().count or 0)
    pages = max(1, math.ceil(total / EVENTS_PER_PAGE)) if total > 0 else 1
    return min(max(1, page), pages)

# =============================
# BLOCK 4 — UI & Handlers
# =============================

with gr.Blocks(css=CUSTOM_CSS, title=f"{APP_TITLE} · {__APP_VERSION__}") as demo:
    # ----- Header -----
    with gr.Row(elem_classes="kalli-header"):
        if os.path.exists(LOGO_PATH):
            #gr.Image(LOGO_PATH, show_label=False, height=40, width=40, container=False)
            gr.Image(LOGO_PATH, show_label=False, container=False, elem_classes="logo")

        gr.HTML(f"<div><div class='kalli-title'>{APP_TITLE}</div><div class='kalli-subtitle'>{__APP_VERSION__}</div></div>")

    # ----- Tipp des Tages -----
    with gr.Row():
        tipp_md = gr.Markdown(visible=False)
        tipp_btn = gr.HTML(visible=False)
    gr.HTML('<div style="height:1px;background:#3a3a3a;margin:8px 0 14px;border-radius:1px;"></div>')


 # Optional: Ticker (Platzhalter)
   # with gr.Row(elem_classes="ticker-row"):
   #     gr.HTML(
   #         "<div>Aktuelle Hinweise: Termine können sich kurzfristig ändern. Angaben daher ohne Gewähr!"
   #     )

    # ----- Section: Veranstaltungen -----
    gr.Markdown("## Veranstaltungen -Teilnehmerkreis beachten - Angaben ohne Gewähr!")

    # ----- Filterleiste -----
    with gr.Row(elem_id="filterbar"):
        suchfeld = gr.Textbox(label="🔎 Suche", placeholder="z. B. Stammtisch, Infostand … (min. 2 Zeichen)")
        #clear_search = gr.Button("❌", elem_id="btn-clear", scale=0, min_width=48)
        show_all = gr.Checkbox(label="Alle Termine zeigen", value=False)
        start_date_inp = gr.DateTime(label="Ab Datum", include_time=False, type="string", info="leer = Standard (nur kommende)")

    # ----- Navigation & Print -----
    with gr.Row(elem_classes="kalli-actions"):
        clear_search = gr.Button("❌", elem_id="btn-clear", scale=0, min_width=48)
        back_btn = gr.Button("⬅️ Zurück")
        next_btn = gr.Button("Weiter ➡️")
        print_btn = gr.Button("🖨 Drucken", elem_id="btn-print")

    print_evt = print_btn.click(fn=lambda: None, inputs=None, outputs=None, queue=False)
    print_evt.then(
        fn=None,
        js="try{if(document.activeElement){document.activeElement.blur();}}catch(e){} window.print();",
        queue=False
    )

    # Fallback: direkter JS-Listener am Button (manche Gradio-Builds droppen js= am Event)
    demo.load(
        fn=None,
        js="(()=>{const el=document.getElementById('btn-print');if(!el)return;el.addEventListener('click',()=>{try{if(document.activeElement){document.activeElement.blur();}}catch(e){} window.print();},{once:false});})()",
        queue=False
    )

    # ----- Outputs -----
    page_info = gr.Markdown()
    output_box = gr.Markdown(elem_id="kalli-events")
    q_state = gr.State("")
    current_page = gr.State(1)

    # ----- Handler: do_search -----
    def do_search(q, show_all, start_date_val):
        """Search handler.
        Normalisiert die Query (min. 2 Zeichen), ruft die Datenabfrage auf
        und setzt gleichzeitig den internen Zustand (q_state, current_page).
        """
        qs = (q or "").strip()
        if qs and len(qs) < 2:
            md, info, _, _ = search_page("", 1, show_all, start_date_val)
            return md, info, "", 1
        md, info, _, _ = search_page(qs, 1, show_all, start_date_val)
        return md, info, qs, 1

    # ----- Handler: Navigation -----
    def go_back(q, page, show_all, start_date_val):
        """Navigiert eine Seite zurück (sofern vorhanden) und clamped Page-Index.
        Gibt gerenderte Markdown-Liste, Page-Info und die neue Seite zurück.
        """
        p = _clamp_page_for(q, max(1, page-1), show_all, start_date_val)
        md, info, q2, p2 = search_page(q, p, show_all, start_date_val)
        return md, info, p2

    def go_next(q, page, show_all, start_date_val):
        """Navigiert eine Seite vor (sofern vorhanden) und clamped Page-Index.
        Gibt gerenderte Markdown-Liste, Page-Info und die neue Seite zurück.
        """
        p = _clamp_page_for(q, page+1, show_all, start_date_val)
        md, info, q2, p2 = search_page(q, p, show_all, start_date_val)
        return md, info, p2

    # ----- Handler: Clear Search -----
    def clear_search_fn(show_all, start_date_val):
        """Setzt Suchfeld und Seite zurück und lädt Standardliste (kommende Termine).
        Liefert außerdem einen leeren q_state, damit Navigation konsistent bleibt.
        """
        md, info, _, _ = search_page("", 1, show_all, start_date_val)
        return md, info, "", 1, ""

    # ----- Hooks -----
    suchfeld.change(fn=do_search, inputs=[suchfeld, show_all, start_date_inp], outputs=[output_box, page_info, q_state, current_page]).then(fn=update_nav_from_info, inputs=[page_info], outputs=[back_btn, next_btn])
    show_all.change(fn=do_search, inputs=[suchfeld, show_all, start_date_inp], outputs=[output_box, page_info, q_state, current_page]).then(fn=update_nav_from_info, inputs=[page_info], outputs=[back_btn, next_btn])
    start_date_inp.change(fn=do_search, inputs=[suchfeld, show_all, start_date_inp], outputs=[output_box, page_info, q_state, current_page]).then(fn=update_nav_from_info, inputs=[page_info], outputs=[back_btn, next_btn])

    back_btn.click(fn=go_back, inputs=[q_state, current_page, show_all, start_date_inp], outputs=[output_box, page_info, current_page]).then(fn=update_nav_from_info, inputs=[page_info], outputs=[back_btn, next_btn])
    next_btn.click(fn=go_next, inputs=[q_state, current_page, show_all, start_date_inp], outputs=[output_box, page_info, current_page]).then(fn=update_nav_from_info, inputs=[page_info], outputs=[back_btn, next_btn])
    clear_search.click(fn=clear_search_fn, inputs=[show_all, start_date_inp], outputs=[output_box, page_info, suchfeld, current_page, q_state]).then(fn=update_nav_from_info, inputs=[page_info], outputs=[back_btn, next_btn])

    # ----- Initial Load -----
    demo.load(fn=do_search, inputs=[suchfeld, show_all, start_date_inp], outputs=[output_box, page_info, q_state, current_page])

    # ----- Tipp Init -----
    def init_tipp():
        """Lädt den 'Tipp des Tages' aus Supabase und zeigt optional einen CTA-Button.
        Gibt zwei Komponenten-Updates zurück: Markdown-Inhalt und CTA-HTML.
        """
        row = load_tipp(supabase)
        if not row:
            return gr.update(visible=False), gr.update(visible=False)
        # md = f"""### {row['title']}
        md = f"""### Mein Tipp: {row['title']}


{row.get('body', '') or ''}"""
        btn = tipp_chip_html(row)
        return gr.update(value=md, visible=True), gr.update(value=btn, visible=bool(btn))

    demo.load(fn=init_tipp, outputs=[tipp_md, tipp_btn], queue=False)

if __name__ == "__main__":
    # Für Deployment (Render, Docker etc.):
    #demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))

    # Für lokalen Test:
    demo.launch()
