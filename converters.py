"""
Модуль для конвертации различных форматов документов в текст
"""
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


def extract_text_from_pages(file_path: str) -> tuple[str | None, str]:
    """Извлекает текст из файла .pages (Apple Pages)."""
    debug = []
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            debug.append(f"📦 Архив содержит {len(file_list)} файлов")
            debug.append(f"Первые файлы: {', '.join(file_list[:5])}")

            # Проверяем формат
            has_iwa = any('.iwa' in f for f in file_list)
            has_xml = any(f.endswith('.xml') for f in file_list)

            if has_iwa:
                debug.append("⚠️ Обнаружен современный формат .iwa (Pages 5.0+)")
                debug.append("📝 Рекомендация: экспортируйте файл как .txt или .docx")
                debug.append("   Файл → Экспортировать → Word/Обычный текст")
                return None, '\n'.join(debug)

            # Метод 1: QuickLook/Preview.txt
            preview_txt_paths = [
                'QuickLook/Preview.txt',
                'preview.txt',
                'Preview.txt'
            ]
            for preview_path in preview_txt_paths:
                if preview_path in file_list:
                    debug.append(f"✅ Найден {preview_path}")
                    with zip_ref.open(preview_path) as txt_file:
                        text = txt_file.read().decode('utf-8', errors='ignore')
                        if text.strip():
                            debug.append(f"✅ Извлечено {len(text)} символов")
                            return text, '\n'.join(debug)

            # Метод 2: XML файлы (старый формат Pages)
            if has_xml:
                xml_files = [f for f in file_list if f.endswith('.xml')]
                debug.append(f"📄 Найдено XML файлов: {len(xml_files)}")

                for xml_file in xml_files:
                    try:
                        with zip_ref.open(xml_file) as xf:
                            content = xf.read()
                            try:
                                tree = ET.fromstring(content)
                                text_parts = []

                                for elem in tree.iter():
                                    if elem.text and elem.text.strip():
                                        text_parts.append(elem.text.strip())
                                    if elem.tail and elem.tail.strip():
                                        text_parts.append(elem.tail.strip())

                                if text_parts:
                                    result = ' '.join(text_parts)
                                    words = [w for w in result.split() if len(w) > 2]
                                    if len(words) > 10:
                                        debug.append(f"✅ Извлечено из {xml_file}: {len(words)} слов")
                                        return ' '.join(words), '\n'.join(debug)
                            except ET.ParseError:
                                pass
                    except Exception as e:
                        debug.append(f"⚠️ {xml_file}: {str(e)[:50]}")

            # Метод 3: Текстовые файлы
            txt_files = [f for f in file_list if f.endswith(('.txt', '.text'))]
            if txt_files:
                for file_name in txt_files:
                    try:
                        with zip_ref.open(file_name) as f:
                            text = f.read().decode('utf-8', errors='ignore')
                            if text.strip():
                                debug.append(f"✅ Извлечено из {file_name}")
                                return text, '\n'.join(debug)
                    except Exception:
                        continue

            debug.append("❌ Не найдено подходящих файлов с текстом")
            return None, '\n'.join(debug)

    except Exception as e:
        debug.append(f"❌ Критическая ошибка: {str(e)}")
        return None, '\n'.join(debug)


def extract_text_from_docx(file_path: str) -> tuple[str | None, str]:
    """Извлекает текст из файла .docx (Microsoft Word)."""
    debug = []
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # DOCX - это тоже ZIP архив
            if 'word/document.xml' not in zip_ref.namelist():
                debug.append("❌ Неверная структура .docx файла")
                return None, '\n'.join(debug)

            with zip_ref.open('word/document.xml') as xml_file:
                tree = ET.parse(xml_file)
                root = tree.getroot()

                # Namespace для Word XML
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

                # Извлекаем текст из параграфов
                paragraphs = []
                for para in root.findall('.//w:p', ns):
                    texts = para.findall('.//w:t', ns)
                    if texts:
                        para_text = ''.join(t.text for t in texts if t.text)
                        if para_text.strip():
                            paragraphs.append(para_text)

                if paragraphs:
                    text = '\n'.join(paragraphs)
                    debug.append(f"✅ Извлечено {len(paragraphs)} параграфов")
                    return text, '\n'.join(debug)

                debug.append("❌ Документ пуст")
                return None, '\n'.join(debug)

    except Exception as e:
        debug.append(f"❌ Ошибка: {str(e)}")
        return None, '\n'.join(debug)


def extract_text_from_txt(file_path: str) -> tuple[str | None, str]:
    """Извлекает текст из обычного текстового файла."""
    debug = []
    for enc in ("utf-8", "cp1251", "cp866", "latin-1"):
        try:
            with open(file_path, "r", encoding=enc) as f:
                text = f.read()
            debug.append(f"✅ Кодировка: {enc}")
            return text, '\n'.join(debug)
        except (UnicodeDecodeError, UnicodeError):
            continue

    debug.append("❌ Не удалось определить кодировку")
    return None, '\n'.join(debug)


def convert_to_text(file_path: str) -> tuple[str | None, str]:
    """
    Универсальная функция конвертации файла в текст.
    Возвращает (text, debug_info).
    """
    file_ext = Path(file_path).suffix.lower()

    converters = {
        '.pages': extract_text_from_pages,
        '.docx': extract_text_from_docx,
        '.txt': extract_text_from_txt,
        '.md': extract_text_from_txt,
        '.text': extract_text_from_txt,
    }

    if file_ext in converters:
        return converters[file_ext](file_path)
    else:
        return None, f"❌ Неподдерживаемый формат: {file_ext}"
