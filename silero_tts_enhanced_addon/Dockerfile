FROM python:3.11-slim

WORKDIR /app

# Без этого print() буферизуется и не попадает в лог аддона
ENV PYTHONUNBUFFERED=1

# libsndfile1 нужен для работы с аудио; без рекомендованных пакетов образ заметно меньше
RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# CPU-версия torch: из PyPI на Linux он тянет около 1,5 ГБ библиотек CUDA, которые аддону не нужны
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir fastapi uvicorn silero-tts==0.0.5 pydantic scipy

COPY *.py /app/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8014"]
