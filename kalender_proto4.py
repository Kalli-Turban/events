import gradio as gr
import json

# JSON-Datei laden
def load_events():
    try:
        with open("json/events.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return [{"titel": "Fehler", "datum": "", "uhrzeit": "", "dauer": "", "ort": "", "kategorie": "Fehler", "link": "", "pdf_url": f"Fehler beim Laden: {e}"}]

# Mehrere Events als Markdown formatieren
def format_event_group(events):
    output = ""
    for e in events:
        output += f"### 📅 {e['titel']}\n"
        output += f"🕓 {e['datum']} – {e['uhrzeit']}"
        if e["dauer"]:
            output += f" ({e['dauer']})"
        output += "\n\n"
        output += f"📍 {e['ort']}\n\n"
        if e["link"]:
            output += f"🔗 [Mehr erfahren]({e['link']})\n"
        if e["pdf_url"]:
            output += f"📄 [PDF öffnen]({e['pdf_url']})\n"
        output += "---\n"
    return output.strip()

# Anzeige der aktuellen Seite (3 Karten)
def show_page(page, kategorie):
    events = load_events()
    filtered = [e for e in events if kategorie in ("Alle", e["kategorie"])]
    if not filtered:
        return "⚠️ Keine Termine gefunden.", gr.update(visible=False), gr.update(visible=False), 0, 0
    per_page = 3
    start = page * per_page
    end = start + per_page
    group = filtered[start:end]
    total_pages = (len(filtered) - 1) // per_page
    return format_event_group(group), gr.update(visible=page > 0), gr.update(visible=page < total_pages), page, total_pages

# Navigation: Seite ändern
def update_page(direction, page, kategorie):
    new_page = page + direction
    return show_page(new_page, kategorie)

# Gradio GUI
with gr.Blocks() as demo:
    gr.Markdown("## 🗓️ KalliGPT Klartext-Kalender – 3 Karten pro Seite")

    with gr.Row():
        kategorie_dropdown = gr.Dropdown(
            choices=["Alle", "Infostand", "Stammtisch"],
            label="Kategorie wählen",
            value="Alle"
        )
        anzeigen_button = gr.Button("🔎 Anzeigen")

    event_markdown = gr.Markdown()
    back_button = gr.Button("← Zurück", visible=False)
    next_button = gr.Button("Weiter →", visible=False)
    page_state = gr.State(0)
    total_state = gr.State(0)

    anzeigen_button.click(fn=show_page, inputs=[page_state, kategorie_dropdown],
                          outputs=[event_markdown, back_button, next_button, page_state, total_state])
    back_button.click(fn=update_page, inputs=[gr.State(-1), page_state, kategorie_dropdown],
                      outputs=[event_markdown, back_button, next_button, page_state, total_state])
    next_button.click(fn=update_page, inputs=[gr.State(1), page_state, kategorie_dropdown],
                      outputs=[event_markdown, back_button, next_button, page_state, total_state])

demo.launch()
