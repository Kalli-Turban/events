
import gradio as gr

# Dummy-Daten
dummy_events = [
    {
        "titel": "Infostand Marienfelde",
        "datum": "2025-08-10",
        "uhrzeit": "10:00 Uhr",
        "dauer": "2h",
        "ort": "Kaufpark Eiche",
        "kategorie": "Infostand",
        "link": "https://maps.google.com/?q=Kaufpark+Eiche"
    },
    {
        "titel": "Stammtisch Süd",
        "datum": "2025-08-15",
        "uhrzeit": "19:00 Uhr",
        "dauer": "",
        "ort": "Gasthaus zur Linde",
        "kategorie": "Stammtisch",
        "link": ""
    }
]

def format_events(kategorie_filter):
    filtered = [e for e in dummy_events if kategorie_filter in ("Alle", e["kategorie"])]
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
            output += f"🔗 [Mehr erfahren]({e['link']})\n\n"
        output += "---\n"
    return output.strip()

with gr.Blocks() as demo:
    with gr.Tabs():
        with gr.Tab("📋 Termine anzeigen"):
            all_output = gr.Markdown(format_events("Alle"))

        with gr.Tab("🔍 Filtern & Suchen"):
            with gr.Row():
                kategorie_dropdown = gr.Dropdown(
                    choices=["Alle", "Infostand", "Stammtisch"],
                    label="Kategorie wählen",
                    value="Alle"
                )
                filter_button = gr.Button("🔎 Filtern")
            filtered_output = gr.Markdown()
            filter_button.click(fn=format_events, inputs=kategorie_dropdown, outputs=filtered_output)

demo.launch()
