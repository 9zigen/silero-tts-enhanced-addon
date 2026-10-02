# Silero TTS Enhanced Engine - Home Assistant Add-on

Local, fast, and high-quality Text-to-Speech engine for Home Assistant, based on [Silero Models](https://github.com/snakers4/silero-models) and the [silero-tts wrapper by daswer123](https://github.com/daswer123/silero-tts-enhanced).

## Features
- **Fully Local:** Models and Silero's model list are saved in `/data`; after the first download it works without internet.
- **Text Preparation:** Numbers to words (Russian "1"/"2" agree with the next noun, negative numbers, long numbers digit by digit), Latin words transliterated in Russian text, long messages split into sentences.
- **SSML:** Pauses (`<break time="3s"/>`), speed and pitch (`<prosody>`), paragraphs and sentences on v5 models.
- **Stress and Ё:** Automatic stress and `ё` placement (switchable), plus manual stress with `+` (`зам+ок`).
- **RAM Caching:** Keeps up to N models loaded at once (default 2, about 230 MB each; set it on the add-on Configuration tab). Other models load from the disk cache.
- **Any Silero Model:** Models are downloaded on first use, e.g. `v5_5_ru`, `v5_ru`, `v3_en`.

See the add-on documentation (DOCS.md) for details, examples and known limits.

## Installation
1. Go to Home Assistant -> **Settings** -> **Add-ons** -> **Add-on Store**.
2. Click the three dots (top right) -> **Repositories**.
3. Add the URL of this repository.
4. Refresh and search for **Silero TTS Enhanced Engine**.
5. Click **Install**, then **Start**.

## Integration
To use this Add-on seamlessly in Home Assistant (with UI configuration), install the companion [Silero-tts-enhanced](https://github.com/indevor/silero-tts-enhanced-hacs).

## 📝 Acknowledgements & License
This project is an unofficial wrapper/integration. The core Text-to-Speech neural models are developed and owned by the [Silero Team](https://github.com/snakers4/silero-models).
The models are published under the **CC BY-NC** (Non-Commercial) license. Please respect the authors' rights and use this integration strictly for personal, non-commercial purposes.

-----------------------------

# Усовершенствованный движок Silero TTS — дополнение для Home Assistant

Локальный, быстрый и высококачественный движок преобразования текста в речь для Home Assistant, основанный на [моделях Silero](https://github.com/snakers4/silero-models) и [обёртке silero-tts от daswer123](https://github.com/daswer123/silero-tts-enhanced).

## Особенности
- **Полностью локальный:** Модели и список моделей Silero сохраняются в `/data`; после первой загрузки работает без интернета.
- **Подготовка текста:** Числа словами (русские «один»/«два» согласуются со следующим существительным, отрицательные числа, длинные числа по цифрам), транслитерация латиницы в русском тексте, длинные сообщения делятся на предложения.
- **SSML:** Паузы (`<break time="3s"/>`), скорость и высота голоса (`<prosody>`), абзацы и предложения на моделях v5.
- **Ударения и Ё:** Автоматическая расстановка ударений и `ё` (отключается), а также ручное ударение через `+` (`зам+ок`).
- **Кэширование в RAM:** Держит до N моделей загруженными одновременно (по умолчанию 2, около 230 МБ каждая; настраивается на вкладке «Конфигурация» аддона). Остальные модели подгружаются с диска.
- **Любая модель Silero:** Модели скачиваются при первом использовании, например `v5_5_ru`, `v5_ru`, `v3_en`.

Подробности, примеры и известные ограничения — в документации аддона (DOCS.md).

## Установка
1. Перейдите в Home Assistant -> **Настройки** -> **Дополнения** -> **Магазин дополнений**.
2. Нажмите на три точки (вверху справа) -> **Репозитории**.
3. Добавьте URL этого репозитория.
4. Обновите страницу и найдите **Silero TTS Enhanced Engine**.
5. Нажмите **Установить**, затем **Запустить**.

## Интеграция
Чтобы беспрепятственно использовать это дополнение в Home Assistant (с настройкой интерфейса), установите сопутствующее приложение [Silero-tts-enhanced](https://github.com/indevor/silero-tts-enhanced-hacs).

## 📝 Благодарности и лицензия
Этот проект является неофициальной оболочкой/интеграцией. Основные нейронные модели преобразования текста в речь разработаны и принадлежат [команде Silero](https://github.com/snakers4/silero-models).
Модели опубликованы под лицензией **CC BY-NC** (некоммерческое использование). Пожалуйста, уважайте права авторов и используйте эту интеграцию строго в личных, некоммерческих целях.
