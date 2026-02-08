"""
Audiobook Maker — Конвертер текста в аудиокниги на русском языке
Использует Silero TTS v5 с автоматическими ударениями и омографами

Точка входа приложения.
"""

import gradio as gr
from ui import create_app, CUSTOM_CSS

app = create_app()

if __name__ == "__main__":
    dark_theme = gr.themes.Soft(
        primary_hue=gr.themes.colors.slate,
        secondary_hue=gr.themes.colors.slate,
        neutral_hue=gr.themes.colors.slate,
    ).set(
        body_background_fill="#1a1d24",
        body_background_fill_dark="#1a1d24",
        block_background_fill="#252a33",
        block_background_fill_dark="#252a33",
        input_background_fill="#2d3440",
        input_background_fill_dark="#2d3440",
        button_primary_background_fill="#4a6785",
        button_primary_background_fill_hover="#5b7c99",
        button_primary_text_color="#e4e6eb",
    )

    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        theme=dark_theme,
        css=CUSTOM_CSS,
    )
