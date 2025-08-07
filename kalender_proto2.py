import gradio as gr
import json

# 🧾 JSON-Datei laden
def load_events():
    try:
        with open("json/events.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return [{"titel": "Fehler", "datum": "", "uhrzeit": "", "dauer": "", "ort": "", "kategorie": "Fehler", "link": "", "pdf_url": f"Fehler beim Laden: {e}"}]

# 📋 Events formatieren
def format_events(kategorie_filter):
    events = load_events()
    filtered = [e for e in events if kategorie_filter in ("Alle", e["kategorie"])]
    if not filtered:
        return "⚠️ Keine Termine gefunden."
    output = ""
    for e in filtered:
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

# 🎛️ Gradio GUI
with gr.Blocks() as demo:
    gr.Markdown("## 🗓️ KalliGPT Klartext-Kalender 2.0")

    with gr.Row():
        kategorie_dropdown = gr.Dropdown(
            choices=["Alle", "Infostand", "Stammtisch"],
            label="Kategorie wählen",
            value="Alle"
        )
        filter_button = gr.Button("🔎 Filtern")
    
    output_box = gr.Markdown()
    filter_button.click(fn=format_events, inputs=kategorie_dropdown, outputs=output_box)
    demo.load(fn=lambda: format_events("Alle"), outputs=output_box)

demo.launch()
