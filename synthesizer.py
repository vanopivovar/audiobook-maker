"""
Ядро синтеза речи: генерация аудио, экспорт, логирование
"""

import os
import re
import time
import wave
import zipfile
import numpy as np
import gradio as gr
from pathlib import Path
from pydub import AudioSegment

from config import SAMPLE_RATE, OUTPUT_DIR, SPEAKERS, FORMATS
from tts_model import model
from text_processing import preprocess_text, split_into_sentences, split_long_sentence
from converters import convert_to_text


def create_detailed_log(
    files: list[dict],
    total_time: float,
    settings: dict
) -> str:
    """
    Создает детальный лог-файл с результатами синтеза.
    Возвращает путь к лог-файлу.
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_filename = f"audiobook_log_{timestamp}.txt"
    log_path = OUTPUT_DIR / log_filename

    # Подсчет статистики
    total_files = len(files)
    successful_files = sum(1 for f in files if "✅" in f["Статус"])
    failed_files = sum(1 for f in files if "❌" in f["Статус"])
    total_errors = sum(f.get("Ошибки", 0) for f in files)

    # Вычисление общего размера
    total_size_mb = 0.0
    for f in files:
        if f["Размер"] != "-":
            try:
                size_str = f["Размер"].replace(" MB", "")
                total_size_mb += float(size_str)
            except (ValueError, AttributeError):
                pass

    # Формирование содержимого лога
    log_content = []
    log_content.append("=" * 70)
    log_content.append("AUDIOBOOK MAKER - ДЕТАЛЬНЫЙ ОТЧЕТ О СИНТЕЗЕ")
    log_content.append("=" * 70)
    log_content.append("")

    # Общая информация
    log_content.append("📊 ОБЩАЯ СТАТИСТИКА")
    log_content.append("-" * 70)
    log_content.append(f"Дата и время: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_content.append(f"Общее время выполнения: {total_time:.2f} сек ({total_time/60:.2f} мин)")
    log_content.append(f"Всего файлов: {total_files}")
    log_content.append(f"  ✅ Успешно: {successful_files}")
    log_content.append(f"  ❌ Ошибок: {failed_files}")
    log_content.append(f"Общий размер: {total_size_mb:.2f} MB")
    log_content.append(f"Количество ошибок при обработке фрагментов: {total_errors}")
    log_content.append("")

    # Настройки синтеза
    log_content.append("⚙️ НАСТРОЙКИ СИНТЕЗА")
    log_content.append("-" * 70)
    log_content.append(f"Голос: {settings.get('voice', 'N/A')}")
    log_content.append(f"Скорость: {settings.get('speed', 'N/A')}x")
    log_content.append(f"Формат: {settings.get('format', 'N/A')}")
    log_content.append("")

    # Детальная информация о файлах
    log_content.append("📁 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О ФАЙЛАХ")
    log_content.append("-" * 70)
    for i, file in enumerate(files, 1):
        log_content.append(f"\n{i}. {file['Файл']}")
        log_content.append(f"   Статус: {file['Статус']}")
        log_content.append(f"   Прогресс: {file['Прогресс']}")
        log_content.append(f"   Размер: {file['Размер']}")
        log_content.append(f"   Время обработки: {file['Время']}")
        log_content.append(f"   Обработано фрагментов: {file['Фрагменты']}")
        if file.get('Ошибки', 0) > 0:
            log_content.append(f"   ⚠️ Ошибок: {file['Ошибки']}")

    log_content.append("")
    log_content.append("=" * 70)
    log_content.append("Сгенерировано Audiobook Maker на базе Silero TTS v5")
    log_content.append("=" * 70)

    # Запись в файл
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_content))

    return str(log_path)


def create_archive_with_files(files: list, log_file: str) -> str:
    """
    Создает ZIP-архив со всеми файлами и логом.
    Возвращает путь к архиву.
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    archive_name = f"audiobook_bundle_{timestamp}.zip"
    archive_path = OUTPUT_DIR / archive_name

    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in files:
            zipf.write(file_path, Path(file_path).name)
        if log_file and Path(log_file).exists():
            zipf.write(log_file, Path(log_file).name)

    return str(archive_path)


def preview_voice(speaker_name: str) -> tuple[str, str]:
    """Создает предпрослушивание выбранного голоса."""
    try:
        speaker = SPEAKERS.get(speaker_name, "xenia")
        # Извлекаем имя из строки вида "Ксения (женский)"
        name = speaker_name.split('(')[0].strip()
        text = f"Привет! Я {name}."

        audio = model.apply_tts(
            text=text,
            speaker=speaker,
            sample_rate=SAMPLE_RATE,
            put_accent=True,
            put_yo=True,
        )

        # Сохраняем во временный файл
        preview_path = OUTPUT_DIR / f"preview_{speaker}.wav"
        audio_int16 = (audio.numpy() * 32767).astype(np.int16)
        segment = AudioSegment(
            audio_int16.tobytes(),
            frame_rate=SAMPLE_RATE,
            sample_width=2,
            channels=1,
        )
        segment.export(str(preview_path), format="wav")

        return str(preview_path), f"✅ {speaker_name}"
    except Exception as e:
        return None, f"❌ Ошибка: {str(e)}"


def synthesize_text(
    text: str,
    speaker_name: str,
    speed: float,
    pause_between_sentences: float,
    output_format: str,
    mp3_tags_title: str,
    mp3_tags_artist: str,
    progress=gr.Progress(track_tqdm=False),
):
    """
    Синтезирует речь из текста с потоковой записью на диск.
    Не накапливает аудио в RAM — подходит для больших текстов.
    Возвращает (audio_path, download_path, log).
    """

    if not text or not text.strip():
        yield None, None, "❌ Введите текст для озвучивания."
        return

    speaker = SPEAKERS.get(speaker_name, "xenia")
    fmt = FORMATS.get(output_format, FORMATS["MP3 (192 kbps)"])

    # Предобрабатываем текст
    text = preprocess_text(text)
    sentences = split_into_sentences(text)

    if not sentences:
        yield None, None, "❌ Текст не содержит предложений."
        return

    # Разбиваем длинные предложения
    all_chunks = []
    for s in sentences:
        all_chunks.extend(split_long_sentence(s))

    total = len(all_chunks)
    log_lines = [
        f"📖 Найдено фрагментов: {total}",
        f"🎙 Голос: {speaker_name} ({speaker})",
        f"⏩ Скорость: {speed}x",
        f"💿 Формат: {output_format}",
        "",
    ]

    # Подготавливаем паузу как int16 (один раз)
    pause_samples = int(SAMPLE_RATE * pause_between_sentences)
    pause_int16 = np.zeros(pause_samples, dtype=np.int16)

    # Временный WAV-файл для потоковой записи
    timestamp = int(time.time())
    safe_title = re.sub(r'[^\w\s-]', '', mp3_tags_title or "audiobook").strip()[:50]
    safe_title = re.sub(r'\s+', '_', safe_title) if safe_title else "audiobook"
    temp_wav_path = OUTPUT_DIR / f"_temp_{safe_title}_{timestamp}.wav"

    start_time = time.time()
    failed_chunks = 0
    written_frames = 0

    # Потоковая запись: каждый фрагмент сразу пишется на диск
    wav_file = wave.open(str(temp_wav_path), 'wb')
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)  # int16
    wav_file.setframerate(SAMPLE_RATE)

    try:
        for i, chunk in enumerate(all_chunks):
            progress((i + 1) / total, desc=f"Озвучивание {i+1}/{total}...")

            try:
                audio = model.apply_tts(
                    text=chunk,
                    speaker=speaker,
                    sample_rate=SAMPLE_RATE,
                    put_accent=True,
                    put_yo=True,
                    put_stress_homo=True,
                    put_yo_homo=True,
                )
                # Конвертируем и записываем сразу на диск
                audio_int16 = (audio.numpy() * 32767).astype(np.int16)
                wav_file.writeframes(audio_int16.tobytes())
                wav_file.writeframes(pause_int16.tobytes())
                written_frames += len(audio_int16) + pause_samples
            except Exception as e:
                failed_chunks += 1
                log_lines.append(f"⚠️ Ошибка в фрагменте {i+1}/{total}: {str(e)[:100]}")
                log_lines.append(f"   Текст: {chunk[:80]}...")

                if failed_chunks > total * 0.3:
                    wav_file.close()
                    temp_wav_path.unlink(missing_ok=True)
                    error_msg = (
                        f"\n\n❌ Критическая ошибка: слишком много неудачных фрагментов ({failed_chunks}/{total})\n"
                        f"Возможные причины:\n"
                        f"• Текст содержит некорректные символы\n"
                        f"• Недостаточно памяти\n\n"
                        f"Попробуйте:\n"
                        f"• Разделить текст на части\n"
                        f"• Проверить кодировку файла"
                    )
                    yield None, None, "\n".join(log_lines) + error_msg
                    return
                continue
    finally:
        wav_file.close()

    if written_frames == 0:
        temp_wav_path.unlink(missing_ok=True)
        yield None, None, "\n".join(log_lines) + "\n\n❌ Не удалось синтезировать ни одного фрагмента."
        return

    # Формируем итоговый файл
    filename = f"{safe_title}_{speaker}_{timestamp}{fmt['ext']}"
    output_path = OUTPUT_DIR / filename

    # Конвертация: изменение скорости и/или формата
    # pydub загружает с диска, не из RAM целиком
    segment = AudioSegment.from_wav(str(temp_wav_path))

    if speed != 1.0:
        new_frame_rate = int(SAMPLE_RATE * speed)
        segment = segment._spawn(
            segment.raw_data,
            overrides={"frame_rate": new_frame_rate},
        )
        segment = segment.set_frame_rate(SAMPLE_RATE)

    # Экспорт с тегами
    export_params = dict(fmt["params"])
    tags = {}
    if mp3_tags_title:
        tags["title"] = mp3_tags_title
        tags["album"] = mp3_tags_title
    if mp3_tags_artist:
        tags["artist"] = mp3_tags_artist
    if tags:
        export_params["tags"] = tags

    segment.export(str(output_path), format=fmt["format"], **export_params)

    # Удаляем временный WAV
    duration_sec = len(segment) / 1000
    del segment
    temp_wav_path.unlink(missing_ok=True)

    elapsed = time.time() - start_time
    file_size_mb = output_path.stat().st_size / (1024 * 1024)

    log_lines.extend([
        f"✅ Готово за {elapsed:.1f} сек",
        f"🕐 Длительность: {duration_sec:.1f} сек ({duration_sec/60:.1f} мин)",
        f"📁 Размер: {file_size_mb:.1f} MB",
        f"💾 Файл: {filename}",
    ])

    yield str(output_path), str(output_path), "\n".join(log_lines)


def synthesize_file(
    file,
    speaker_name: str,
    speed: float,
    pause_between_sentences: float,
    output_format: str,
    mp3_tags_title: str,
    mp3_tags_artist: str,
    progress=gr.Progress(track_tqdm=False),
):
    """Синтезирует речь из загруженного файла."""
    if file is None:
        yield None, None, "❌ Загрузите текстовый файл."
        return

    file_path = file if isinstance(file, str) else file.name

    # Универсальная конвертация через модуль converters
    text, debug_info = convert_to_text(file_path)

    if text is None:
        error_msg = f"❌ Не удалось извлечь текст из файла.\n\n🔍 Диагностика:\n{debug_info}"
        yield None, None, error_msg
        return

    if not text.strip():
        yield None, None, "❌ Файл пуст."
        return

    # Если заголовок не задан — берём имя файла
    if not mp3_tags_title:
        mp3_tags_title = Path(file_path).stem

    yield from synthesize_text(
        text, speaker_name, speed, pause_between_sentences,
        output_format, mp3_tags_title, mp3_tags_artist, progress,
    )
