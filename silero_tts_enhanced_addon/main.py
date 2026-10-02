import os
import tempfile
import shutil
from fastapi import FastAPI, Response, HTTPException
from pydantic import BaseModel

# === НАСТРОЙКА ПОСТОЯННОЙ ПАМЯТИ (ЧТОБЫ МОДЕЛИ НЕ КАЧАЛИСЬ ПРИ РЕСТАРТЕ) ===
PERSISTENT_DIR = "/data/silero_cache"

if not os.path.exists("/data"):
    PERSISTENT_DIR = "./silero_cache"
    
os.makedirs(PERSISTENT_DIR, exist_ok=True)
os.environ["TORCH_HOME"] = PERSISTENT_DIR

# Безопасный поиск папки и создание симлинка
try:
    # Импортируем конкретный файл, у которого точно есть путь
    from silero_tts import silero_tts as st_module
    lib_dir = os.path.dirname(st_module.__file__)
    models_dir = os.path.join(lib_dir, "silero_models")

    # Если это еще не симлинк, удаляем папку и создаем ссылку на /data
    if not os.path.islink(models_dir):
        if os.path.exists(models_dir):
            shutil.rmtree(models_dir)
        os.symlink(PERSISTENT_DIR, models_dir)
        print(f"Симлинк кэша успешно создан: {models_dir} -> {PERSISTENT_DIR}")
except Exception as e:
    print(f"Внимание: Не удалось настроить жесткий кэш моделей: {e}")
# ===========================================================================

from silero_tts.silero_tts import SileroTTS

app = FastAPI()

tts_engine = None
current_model = None

class TTSRequest(BaseModel):
    text: str
    voice: str = "aidar"
    language: str = "ru"
    model_id: str = "v5_ru"
    sample_rate: int = 48000
    put_accent: bool = True
    put_yo: bool = True

QUOTES = "\"'`“”„‟‘’‚«»"

def clean(value: str) -> str:
    # Умные кавычки и пробелы из полей интеграции HA ломают поиск модели в конфиге
    return value.strip().strip(QUOTES).strip()

@app.post("/tts")
def generate_tts(req: TTSRequest):
    global tts_engine, current_model
    model_id = clean(req.model_id)
    language = clean(req.language)
    voice = clean(req.voice)
    try:
        if tts_engine is None or current_model != model_id:
            print(f"Загрузка модели: {model_id}")
            tts_engine = SileroTTS(model_id=model_id, language=language, speaker=voice)
            current_model = model_id

        tts_engine.put_accent = req.put_accent
        tts_engine.put_yo = req.put_yo

        if getattr(tts_engine, 'language', '') != language:
            tts_engine.change_language(language)
        if getattr(tts_engine, 'speaker', '') != voice:
            tts_engine.change_speaker(voice)
            
        if hasattr(tts_engine, 'change_sample_rate'):
            tts_engine.change_sample_rate(req.sample_rate)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            temp_path = tmp.name
            
        print(f"Генерация: текст='{req.text}', голос={voice}")
        tts_engine.tts(req.text, temp_path)
        
        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            raise Exception("Файл не сгенерировался (0 байт). Ошибка библиотеки Silero.")
            
        with open(temp_path, "rb") as f:
            audio = f.read()
            
        os.remove(temp_path)
        print(f"Успех! Отправлено {len(audio)} байт.")
        return Response(content=audio, media_type="audio/wav")

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Неизвестная модель или язык: model_id={model_id!r}, language={language!r} (нет ключа {e})")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
