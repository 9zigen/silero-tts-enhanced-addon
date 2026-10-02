import gc
import io
import json
import os
import shutil
import threading
import time
import wave
from collections import OrderedDict
from contextlib import asynccontextmanager

import requests
import torch
import yaml
from fastapi import FastAPI, Response, HTTPException
from pydantic import BaseModel

# === НАСТРОЙКА ПОСТОЯННОЙ ПАМЯТИ (ЧТОБЫ МОДЕЛИ НЕ КАЧАЛИСЬ ПРИ РЕСТАРТЕ) ===
PERSISTENT_DIR = "/data/silero_cache"

if not os.path.exists("/data"):
    PERSISTENT_DIR = os.path.abspath("./silero_cache")

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

import silero_tts.silero_tts as st_module
from silero_tts.silero_tts import SileroTTS
import textprep

# Библиотека падает при создании движка на языках без числительных (ua, tt, ...)
st_module.NumberToText = textprep.number_converter

MODELS_CONFIG_URL = "https://raw.githubusercontent.com/snakers4/silero-models/master/models.yml"


def refresh_models_config():
    # Список моделей лежит внутри контейнера и качается заново при каждом его пересоздании.
    # С сетью обновляем и сохраняем копию в /data, без сети берём копию, чтобы работать офлайн
    live = os.path.join(os.path.dirname(st_module.__file__), "latest_silero_models.yml")
    saved = os.path.join(PERSISTENT_DIR, "latest_silero_models.yml")
    try:
        response = requests.get(MODELS_CONFIG_URL, timeout=10)
        response.raise_for_status()
        if "tts_models" not in yaml.safe_load(response.text):
            raise ValueError("в ответе нет списка моделей")
        with open(saved, "w", encoding="utf-8") as f:
            f.write(response.text)
        shutil.copyfile(saved, live)
    except Exception as e:
        if os.path.exists(saved):
            shutil.copyfile(saved, live)
            print(f"Список моделей не обновлён ({type(e).__name__}), используется сохранённая копия")
        else:
            print(f"Внимание: список моделей не загружен ({type(e).__name__}), он понадобится при первом запросе")


refresh_models_config()


def read_option(name, default):
    try:
        with open("/data/options.json", encoding="utf-8") as f:
            return int(json.load(f).get(name, default))
    except (OSError, ValueError, TypeError):
        return default


# Одна загруженная модель занимает около 230 МБ ОЗУ
MODEL_CACHE_SIZE = max(1, read_option("model_cache_size", 2))

engines = OrderedDict()  # (model_id, language) -> SileroTTS, последний использованный в конце
lock = threading.Lock()

LAST_MODELS = os.path.join(PERSISTENT_DIR, "last_models.json")
remembered = None


def remember_models():
    # Запоминаем, какие модели были в работе, чтобы после перезапуска загрузить их заранее.
    # Пишем только при изменении списка: на SD-карте лишние записи ни к чему
    global remembered
    current = [list(key) for key in engines]
    if current == remembered:
        return
    remembered = current
    try:
        with open(LAST_MODELS, "w", encoding="utf-8") as f:
            json.dump(current, f)
    except OSError as e:
        print(f"Не удалось сохранить список моделей: {e}")


def warm_up(engine):
    # Первый вызов модели заметно медленнее следующих, поэтому делаем его заранее
    script = textprep.lang_data.get(engine.language, {}).get("script")
    engine.tts_model.apply_tts(text="Привет." if script == "cyrillic" else "Hello.",
                               speaker=engine.tts_model.speakers[0],
                               sample_rate=max(engine.get_available_sample_rates()))


def preload_models():
    try:
        with open(LAST_MODELS, encoding="utf-8") as f:
            saved = [tuple(item) for item in json.load(f)][-MODEL_CACHE_SIZE:]
    except (OSError, ValueError, TypeError):
        return
    for model_id, language in saved:
        started = time.perf_counter()
        try:
            with lock:
                warm_up(get_engine(model_id, language))
            print(f"Модель {model_id} ({language}) загружена и прогрета за {time.perf_counter() - started:.1f} с")
        except Exception as e:
            print(f"Не удалось заранее загрузить модель {model_id} ({language}): {e}")


@asynccontextmanager
async def lifespan(app):
    # В фоне, чтобы аддон сразу начал отвечать; запрос к той же модели просто подождёт загрузки
    threading.Thread(target=preload_models, daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)


class TTSRequest(BaseModel):
    text: str
    voice: str = "aidar"
    language: str = "ru"
    model_id: str = "v5_ru"
    sample_rate: int = 48000
    put_accent: bool = True
    put_yo: bool = True


def get_engine(model_id: str, language: str) -> SileroTTS:
    key = (model_id, language)
    if key in engines:
        engines.move_to_end(key)
        remember_models()
        return engines[key]

    available = SileroTTS.get_available_models()
    if model_id not in available.get(language, []):
        known = ", ".join(available.get(language, [])) or f"язык не поддерживается (доступно: {', '.join(available)})"
        raise HTTPException(status_code=400, detail=f"Модель {model_id!r} недоступна для языка {language!r}: {known}")

    # Освобождаем место до загрузки, чтобы в памяти не было MODEL_CACHE_SIZE + 1 моделей
    while len(engines) >= MODEL_CACHE_SIZE:
        old_model, old_language = engines.popitem(last=False)[0]
        print(f"Модель {old_model} ({old_language}) выгружена из памяти")
    gc.collect()

    print(f"Загрузка модели: {model_id}")
    sample_rate = max(SileroTTS.get_available_sample_rates_static(language, model_id))
    engines[key] = SileroTTS(model_id=model_id, language=language, sample_rate=sample_rate)
    remember_models()
    return engines[key]


def synthesize(engine, text, voice, sample_rate, put_accent, put_yo):
    # Движок не меняем: голос, частота и флаги идут прямо в модель, поэтому кэш безопасно делить
    ssml = textprep.extract_ssml(text)
    if ssml:
        jobs = [{"ssml_text": textprep.prepare_ssml(ssml, engine.language)}]
    else:
        prepared = textprep.prepare_text(text, engine.language)
        jobs = [{"text": chunk} for chunk in textprep.split_chunks(prepared)]

    buffer = io.BytesIO()
    frames = 0
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for job in jobs:
            try:
                audio = engine.tts_model.apply_tts(speaker=voice, sample_rate=sample_rate,
                                                   put_accent=put_accent, put_yo=put_yo, **job)
            except ValueError as e:
                if ssml:
                    raise HTTPException(status_code=400, detail=f"Некорректный SSML: {e}")
                print(f"Фрагмент пропущен: {e}")
                continue
            except Exception as e:
                # Обычный текст режется на куски заранее, до лимита доходит только SSML
                if "too long" in str(e):
                    raise HTTPException(status_code=413, detail="Текст слишком длинный для модели (около 1000 символов), разбейте его на части")
                raise
            pcm = (audio * 32767).numpy().astype("int16")
            wav.writeframes(pcm.tobytes())
            frames += len(pcm)

    if not frames:
        raise HTTPException(status_code=422, detail="Нечего озвучивать: модель не смогла обработать текст")
    return buffer.getvalue(), frames / sample_rate


@app.get("/status")
def status():
    return {"cache_size": MODEL_CACHE_SIZE,
            "torch_threads": torch.get_num_threads(),
            "cached_models": [{"model_id": m, "language": l} for m, l in engines]}


@app.get("/models")
def list_models():
    return SileroTTS.get_available_models()


@app.get("/voices")
def list_voices(model_id: str = "v5_ru", language: str = "ru"):
    model_id = textprep.clean(model_id)
    language = textprep.normalize_language(language)
    with lock:
        engine = get_engine(model_id, language)
        return {"model_id": model_id, "language": language, "voices": list(engine.tts_model.speakers)}


@app.post("/tts")
def generate_tts(req: TTSRequest):
    model_id = textprep.clean(req.model_id)
    language = textprep.normalize_language(req.language)
    voice = textprep.clean(req.voice)
    try:
        requested = time.perf_counter()
        with lock:
            acquired = time.perf_counter()
            engine = get_engine(model_id, language)
            loaded = time.perf_counter()

            speakers = engine.tts_model.speakers
            if voice not in speakers:
                raise HTTPException(status_code=400, detail=f"Голос {voice!r} недоступен для модели {model_id!r}: {', '.join(speakers)}")

            sample_rate = req.sample_rate
            supported = engine.get_available_sample_rates()
            if sample_rate not in supported:
                sample_rate = max(supported)
                print(f"Частота {req.sample_rate} не поддерживается моделью {model_id}, используется {sample_rate}")

            print(f"Генерация: текст='{req.text}', голос={voice}")
            synthesis_started = time.perf_counter()
            audio, seconds = synthesize(engine, req.text, voice, sample_rate, req.put_accent, req.put_yo)
            finished = time.perf_counter()

        timing = f"синтез {finished - synthesis_started:.2f} с"
        if loaded - acquired > 0.01:
            timing += f", загрузка модели {loaded - acquired:.2f} с"
        if acquired - requested > 0.05:
            timing += f", ожидание очереди {acquired - requested:.2f} с"
        print(f"Успех! Отправлено {len(audio) // 1024} КБ, аудио {seconds:.1f} с: {timing}.")
        return Response(content=audio, media_type="audio/wav")

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
