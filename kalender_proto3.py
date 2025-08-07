import gradio as gr
import json

# JSON-Datei laden
def load_events():
    try:
        with open("json/events.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return [{"titel": "Fehler", "datum": "", "uhrzeit": "", "dauer": "", "ort": "", "kategorie": "Fehler", "link": "", "pdf_url": f"Fehler beim Laden: {e}"}]

# Einzelevent als Markdown-Text formatieren
def format_event(event):
    output = f"### 📅 {event['titel']}\n"
    output += f"🕓 {event['datum']} – {event['uhrzeit']}"
    if event["dauer"]:
        output += f" ({event['dauer']})"
    output += "\n\n"
    output += f"📍 {event['ort']}\n\n"
    if event["link"]:
        output += f"🔗 [Mehr erfahren]({event['link']})\n"
    if event["pdf_url"]:
        output += f"📄 [PDF öffnen]({event['pdf_url']})\n"
    return output.strip()

# Anzeige der aktuellen Karte basierend auf Index & Kategorie
def show_event(index, kategorie):
    events = load_events()
    filtered = [e for e in events if kategorie in ("Alle", e["kategorie"])]
    if not filtered:
        return "⚠️ Keine Termine gefunden.", gr.update(visible=False), gr.update(visible=False), 0, 0
    event = filtered[index]
    return format_event(event), gr.update(visible=index > 0), gr.update(visible=index < len(filtered) - 1), index, len(filtered)

# Navigation: weiter oder zurück
def update_index(direction, index, kategorie):
    new_index = index + direction
    return show_event(new_index, kategorie)

# Gradio GUI
with gr.Blocks() as demo:
    gr.Markdown("## 🗓️ KalliGPT Klartext-Kalender – Kartenansicht mit Blättern")

    with gr.Row():
        kategorie_dropdown = gr.Dropdown(
            choices=["Alle", "Infostand", "Stammtisch"],
            label="Kategorie wählen",
            value="Alle"
        )
        anzeige_button = gr.Button("🔎 Anzeigen")

    event_markdown = gr.Markdown()
    back_button = gr.Button("← Zurück", visible=False)
    next_button = gr.Button("Weiter →", visible=False)
    index_state = gr.State(0)
    total_state = gr.State(0)

    # Aktionen
    anzeige_button.click(fn=show_event, inputs=[index_state, kategorie_dropdown],
                         outputs=[event_markdown, back_button, next_button, index_state, total_state])
    back_button.click(fn=update_index, inputs=[gr.State(-1), index_state, kategorie_dropdown],
                      outputs=[event_markdown, back_button, next_button, index_state, total_state])
    next_button.click(fn=update_index, inputs=[gr.State(1), index_state, kategorie_dropdown],
                      outputs=[event_markdown, back_button, next_button, index_state, total_state])

demo.launch()
