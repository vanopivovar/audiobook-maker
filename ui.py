"""
Gradio-интерфейс Audiobook Maker
"""

import gradio as gr
from pathlib import Path

from config import SPEAKERS, FORMATS
from converters import convert_to_text
from text_processing import analyze_text_chapters
from synthesizer import preview_voice, synthesize_text


# ──────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────

CUSTOM_CSS = """
/* Основная тема */
.gradio-container {
    max-width: 1200px !important;
    margin: auto !important;
    background: #1a1d24 !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* Заголовок */
.header-text {
    text-align: center;
    margin-bottom: 2rem;
    padding: 2rem 1rem;
    background: linear-gradient(135deg, #252a33 0%, #2d3440 100%);
    border-radius: 12px;
    border: 1px solid #353b47;
}
.header-text h1 {
    font-size: 2.2rem;
    margin-bottom: 0.5rem;
    color: #e4e6eb;
    font-weight: 600;
}
.header-text p {
    color: #b0b8c1;
    font-size: 0.95rem;
    line-height: 1.6;
}

/* Блоки-секции */
.settings-block, .input-block, .output-block {
    background: #252a33;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    border: 1px solid #353b47;
}

/* Вкладки */
.tab-nav button {
    background: #2d3440 !important;
    color: #b0b8c1 !important;
    border: 1px solid #353b47 !important;
}
.tab-nav button.selected {
    background: #4a6785 !important;
    color: #e4e6eb !important;
}

/* Кнопки */
button {
    background: #4a6785 !important;
    color: #e4e6eb !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.2s !important;
}
button:hover {
    background: #5b7c99 !important;
    transform: translateY(-1px);
}

/* Поля ввода */
input, textarea, select {
    background: #2d3440 !important;
    color: #e4e6eb !important;
    border: 1px solid #353b47 !important;
    border-radius: 8px !important;
}
input:focus, textarea:focus, select:focus {
    border-color: #5b7c99 !important;
    box-shadow: 0 0 0 2px rgba(91, 124, 153, 0.2) !important;
}

/* Checkbox styling for better visibility */
input[type="checkbox"] {
    width: 20px !important;
    height: 20px !important;
    min-width: 20px !important;
    min-height: 20px !important;
    cursor: pointer !important;
    accent-color: #5b7c99 !important;
    border: 2px solid #4a6785 !important;
    border-radius: 4px !important;
    margin-right: 8px !important;
}

input[type="checkbox"]:hover {
    border-color: #5b7c99 !important;
    box-shadow: 0 0 0 2px rgba(91, 124, 153, 0.2) !important;
}

input[type="checkbox"]:checked {
    background-color: #4a6785 !important;
    border-color: #5b7c99 !important;
}

input[type="checkbox"]:focus {
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(91, 124, 153, 0.4) !important;
}

/* Метки */
label {
    color: #b0b8c1 !important;
    font-weight: 500 !important;
    margin-bottom: 0.5rem !important;
}

/* Прогресс-бары */
.progress-bar {
    background: #2d3440 !important;
}
.progress-bar-fill {
    background: linear-gradient(90deg, #4a6785, #5b7c99) !important;
}

/* Аккордеоны */
.accordion {
    background: #2d3440 !important;
    border: 1px solid #353b47 !important;
    border-radius: 8px !important;
}
"""


# ──────────────────────────────────────────────
# Wrapper-функции для двухэтапного UI
# ──────────────────────────────────────────────

def analyze_text_wrapper(text: str):
    """Wrapper для анализа текста через UI."""
    report, can_start = analyze_text_chapters(text)
    return report, gr.update(interactive=can_start), text


def analyze_file_wrapper(file):
    """Wrapper для анализа загруженного файла через UI."""
    if file is None:
        return "❌ Загрузите текстовый файл.", gr.update(interactive=False), None

    file_path = file if isinstance(file, str) else file.name

    # Извлекаем текст из файла
    text, debug_info = convert_to_text(file_path)

    if text is None:
        error_msg = f"❌ Не удалось извлечь текст из файла.\n\n🔍 Диагностика:\n{debug_info}"
        return error_msg, gr.update(interactive=False), None

    if not text.strip():
        return "❌ Файл пуст.", gr.update(interactive=False), None

    # Анализируем извлеченный текст
    report, can_start = analyze_text_chapters(text)

    # Добавляем информацию о файле в отчет
    file_name = Path(file_path).name
    enhanced_report = f"📁 Файл: {file_name}\n\n{report}"

    return enhanced_report, gr.update(interactive=can_start), text


def analyze_universal_wrapper(text_input: str, file_input):
    """Универсальный wrapper для анализа из любого источника (текст или файл)."""
    if file_input is not None:
        return analyze_file_wrapper(file_input)
    elif text_input and text_input.strip():
        return analyze_text_wrapper(text_input)
    else:
        return "❌ Введите текст или загрузите файл.", gr.update(interactive=False), None


def synthesize_with_progress(
    text: str,
    speaker_name: str,
    speed: float,
    pause: float,
    output_format: str,
    mp3_title: str,
    mp3_artist: str,
    progress=gr.Progress(track_tqdm=False)
):
    """Упрощенная обертка для синтеза с прогрессом."""
    for audio_path, download_path, log_text in synthesize_text(
        text, speaker_name, speed, pause, output_format,
        mp3_title, mp3_artist, progress
    ):
        yield audio_path, download_path, log_text


# ──────────────────────────────────────────────
# Построение интерфейса
# ──────────────────────────────────────────────

def create_app() -> gr.Blocks:
    """Создаёт и возвращает Gradio-приложение."""

    with gr.Blocks(title="Audiobook Maker") as app:

        gr.HTML("""
        <div class="header-text">
            <h1>📚 Audiobook Maker</h1>
            <p>Профессиональная конвертация текста в аудиокниги на русском языке</p>
            <p style="font-size: 0.85rem; margin-top: 0.5rem;">
                Silero TTS v5 • Автоматические ударения • Поддержка омографов • Экспорт MP3/WAV/OGG
            </p>
        </div>
        """)

        # ── БЛОК: Настройки синтеза ──
        gr.Markdown("### ⚙️ Настройки синтеза")
        with gr.Row():
            with gr.Column(scale=2):
                speaker = gr.Dropdown(
                    choices=list(SPEAKERS.keys()),
                    value="Ксения (женский)",
                    label="Голос диктора",
                )
                preview_btn = gr.Button("🎧 Прослушать голос", size="sm")
            with gr.Column(scale=1):
                speed = gr.Slider(
                    minimum=0.5, maximum=2.0, value=1.0, step=0.05,
                    label="Скорость речи",
                )
            with gr.Column(scale=1):
                pause = gr.Slider(
                    minimum=0.1, maximum=2.0, value=0.5, step=0.1,
                    label="Пауза (сек)",
                    info="Между предложениями",
                )

        # Превью голоса
        with gr.Row():
            preview_audio = gr.Audio(label="", type="filepath", scale=3)
            preview_status = gr.Textbox(label="", show_label=False, interactive=False, scale=1)

        # ── БЛОК: Параметры экспорта ──
        with gr.Accordion("💿 Параметры экспорта", open=False):
            with gr.Row():
                output_format = gr.Dropdown(
                    choices=list(FORMATS.keys()),
                    value="MP3 (192 kbps)",
                    label="Формат аудио",
                )
                mp3_title = gr.Textbox(
                    label="Название (ID3 Title)",
                    placeholder="Название аудиокниги",
                )
                mp3_artist = gr.Textbox(
                    label="Автор (ID3 Artist)",
                    placeholder="Автор произведения",
                )

        gr.Markdown("---")

        # ── БЛОК: Источник текста ──
        gr.Markdown("### 📝 Источник текста")
        with gr.Tabs():
            with gr.TabItem("✍️ Ввод текста"):
                text_input = gr.Textbox(
                    label="",
                    placeholder=(
                        "Вставьте текст для озвучивания...\n\n"
                        "💡 Совет: для ручной расстановки ударений используйте +\n"
                        "Например: зам+ок (дверной) vs з+амок (крепость)\n\n"
                        "⚠️ Максимальный размер: 5 MB"
                    ),
                    lines=15,
                    max_lines=30,
                )

            with gr.TabItem("📁 Загрузка файла"):
                gr.Markdown("""
                **Поддерживаемые форматы:**
                `.txt` `.md` `.docx` `.pages` (старый формат)
                """)
                file_input = gr.File(
                    label="",
                    file_types=[".txt", ".md", ".docx", ".pages"],
                    type="filepath",
                )

        gr.Markdown("---")

        # ── БЛОК: ЭТАП 1 - АНАЛИЗ ТЕКСТА ──
        gr.Markdown("### 📊 Шаг 1: Анализ текста")
        analyze_btn = gr.Button("🔍 Анализ текста", variant="secondary", size="lg")
        analysis_output = gr.Textbox(
            label="Результаты анализа",
            lines=15,
            interactive=False,
            placeholder="Нажмите 'Анализ текста' чтобы увидеть информацию о тексте..."
        )

        gr.Markdown("---")

        # ── БЛОК: ЭТАП 2 - СИНТЕЗ ──
        gr.Markdown("### 🎙️ Шаг 2: Синтез аудио")
        start_btn = gr.Button(
            "▶️ Запуск синтеза",
            variant="primary",
            size="lg",
            interactive=False
        )

        gr.Markdown("---")

        # ── БЛОК: РЕЗУЛЬТАТЫ ──
        gr.Markdown("### 📁 Результаты")

        with gr.Row():
            with gr.Column():
                player_audio = gr.Audio(
                    label="🎧 Предпрослушивание",
                    type="filepath",
                    interactive=False
                )

            with gr.Column():
                download_output = gr.File(label="📦 Скачать аудиокнигу")

        log_output = gr.Textbox(
            label="Информация о процессе",
            lines=12,
            interactive=False
        )

        gr.Markdown("---")

        with gr.Accordion("💡 Советы и возможности", open=False):
            gr.Markdown("""
            **Ударения:**
            Модель автоматически расставляет ударения. Для ручной коррекции: `зам+ок` (дверной) vs `з+амок` (крепость)

            **Буква Ё:**
            Автоматическое восстановление, но явное написание точнее

            **MP3-теги:**
            Раскройте «Параметры экспорта» для добавления метаданных (название, автор)

            **Длинные тексты:**
            Автоматическая разбивка на фрагменты. Максимальный размер: 5 MB

            **Качество:**
            Рекомендуется MP3 192 kbps для баланса качества и размера
            """)

        # ── Состояние между этапами ──
        analyzed_text = gr.State(value=None)

        # ── Обработчики ──
        common_inputs = [speaker, speed, pause, output_format, mp3_title, mp3_artist]

        preview_btn.click(
            fn=preview_voice,
            inputs=[speaker],
            outputs=[preview_audio, preview_status],
        )

        analyze_btn.click(
            fn=analyze_universal_wrapper,
            inputs=[text_input, file_input],
            outputs=[analysis_output, start_btn, analyzed_text]
        )

        start_btn.click(
            fn=synthesize_with_progress,
            inputs=[analyzed_text] + common_inputs,
            outputs=[player_audio, download_output, log_output]
        )

    return app
