"""
Загрузка и инициализация модели Silero TTS v5
"""

import os
import torch
from config import MODEL_DIR

print("⏳ Загрузка модели Silero TTS v5...")
device = torch.device("cpu")
torch.set_num_threads(int(os.environ.get("TTS_THREADS", "4")))

model_path = MODEL_DIR / "v5_ru.pt"
if not model_path.exists():
    print("📥 Скачивание модели (~100 MB)...")
    try:
        torch.hub.download_url_to_file(
            "https://models.silero.ai/models/tts/ru/v5_ru.pt",
            str(model_path),
        )
    except Exception as e:
        print(f"❌ Не удалось скачать модель: {e}")
        print("Проверьте подключение к интернету или скачайте модель вручную:")
        print(f"  URL: https://models.silero.ai/models/tts/ru/v5_ru.pt")
        print(f"  Путь: {model_path}")
        raise SystemExit(1)

try:
    model = torch.package.PackageImporter(str(model_path)).load_pickle(
        "tts_models", "model"
    )
    model.to(device)
    print("✅ Модель загружена!")
except Exception as e:
    print(f"❌ Не удалось загрузить модель: {e}")
    print(f"Файл модели может быть повреждён. Удалите {model_path} и перезапустите.")
    raise SystemExit(1)
