"""
Утилиты для обработки текста перед синтезом
"""

import re


def split_into_sentences(text: str) -> list[str]:
    """Разбивает текст на предложения с учётом русской пунктуации."""
    text = text.strip()
    if not text:
        return []
    sentences = re.split(r'(?<=[.!?…])\s+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 1]


def analyze_text_chapters(text: str) -> tuple[str, bool]:
    """
    Анализирует текст и возвращает отчет БЕЗ запуска синтеза.
    Возвращает: (отчет_текст, можно_ли_запускать_синтез)
    """
    if not text or not text.strip():
        return "❌ Введите текст для анализа.", False

    text_size_mb = len(text.encode('utf-8')) / (1024 * 1024)
    words = len(text.split())
    estimated_minutes = words / 100

    report_lines = [
        "📊 РЕЗУЛЬТАТЫ АНАЛИЗА",
        "",
        f"📝 Объем текста: {text_size_mb:.2f} MB ({words} слов)",
        f"⏱️ Примерное время синтеза: ~{estimated_minutes:.0f} мин",
        "",
        "✅ Готово к синтезу! Нажмите 'Запуск синтеза' для начала."
    ]

    return "\n".join(report_lines), True


def split_long_sentence(sentence: str, max_chars: int = 900) -> list[str]:
    """
    Silero имеет ограничение ~1000 символов на один вызов.
    Разбиваем длинные предложения по знакам пунктуации.
    """
    if len(sentence) <= max_chars:
        return [sentence]

    chunks = []
    current = ""
    parts = re.split(r'(?<=[,;:–—])\s+', sentence)

    for part in parts:
        if len(current) + len(part) + 1 <= max_chars:
            current = f"{current} {part}".strip() if current else part
        else:
            if current:
                chunks.append(current)
            if len(part) > max_chars:
                words = part.split()
                current = ""
                for w in words:
                    if len(current) + len(w) + 1 <= max_chars:
                        current = f"{current} {w}".strip() if current else w
                    else:
                        if current:
                            chunks.append(current)
                        current = w
            else:
                current = part

    if current:
        chunks.append(current)
    return chunks


def preprocess_text(text: str) -> str:
    """Предобработка текста перед синтезом."""
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('\u00a0', ' ')
    text = re.sub(r'[#*_~`]', '', text)
    return text.strip()
