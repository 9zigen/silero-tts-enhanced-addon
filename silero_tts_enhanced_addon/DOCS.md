# Silero TTS Enhanced Engine

A local, fast, and high-quality text-to-speech synthesizer for your smart home.

This add-on is based on [Silero Models](https://github.com/snakers4/silero-models) neural network models and the [silero-tts](https://github.com/daswer123/silero-tts-enhanced) wrapper by [daswer123](https://github.com/daswer123), extended with its own text preparation.

## 🔥 Features
* **Works locally:** No cloud. Models and Silero's model list are saved in `/data`, so after the first download the add-on also works without internet (a saved copy of the model list is used when it cannot be refreshed).
* **RAM cache:** Keeps several models loaded at once, so switching between them is instant. The number is set on the add-on **Configuration** tab (*Models kept in RAM*, default 2, about 230 MB each). Other models load from the disk cache.
* **Text preparation:**
  * numbers are spoken as words; in Russian "1" and "2" agree with the next noun (`1 час`, `21 минута`, `2 минуты`), negative numbers get "минус", long numbers and codes like `007` are read digit by digit;
  * Latin words and abbreviations in Russian text are transliterated, otherwise the model skips them (`Wi-Fi` → «вай-фай», `USB` → «ю эс би»);
  * long messages are split into sentences automatically.
* **SSML:** pauses, speed and pitch (see below).
* **Stress:** You can explicitly specify stress in complex words by placing a `+` sign before a vowel (e.g., `зам+ок`).

## 🛠 Available Models and Languages
The add-on downloads any model you request from the Integration on first use. An unknown model, voice or language returns an error that lists the valid values.
Most popular:
* **Russian (ru):** `v5_5_ru` (voices: aidar, baya, kseniya, xenia, eugene), `v5_ru`
* **English (en):** `v3_en` (voices: en_0, en_1 ... en_117, random)
* **Ukrainian (ua):** `v4_ua` (voices: mykyta, random)

Language codes: `ru`, `en`, `ua`. Home Assistant's `uk` and region forms like `ru-RU` or `en-US` are accepted too. For other tools: `GET /models` lists models per language, `GET /voices?model_id=v5_5_ru&language=ru` lists voices, `GET /status` shows what is loaded.

## ⚙️ Auto-accent and Ё switches
The two checkboxes in the integration settings are sent as `put_accent` and `put_yo`, and can be overridden per call in `options`.
* **Auto-accent placement** (`put_accent`) lets the model place stress itself. Turn it off to speak without automatic stress; stress marks you set with `+` still work.
* **Auto-placement of the letter Ё** (`put_yo`) restores `ё` in words written with `е` (`елка` → `ёлка`).
* Ambiguous words (homographs such as `замок`, `все`/`всё`) are resolved by the model itself and are not controlled by these two switches.

## 🎚 SSML
Wrap the message in `<speak>…</speak>` (v5 models). Supported tags: `<break time="3s"/>` (also `500ms`), `<prosody rate="slow" pitch="high">`, `<p>`, `<s>`.
Numbers and Latin words inside the text are prepared as usual; tag attributes are left untouched. An SSML message is sent to the model as a single piece, so keep it under about 1000 characters (longer ones are rejected with a clear error; plain text has no such limit).

## 💡 Automation examples
Use plain straight quotes `'` and `"`. Curly quotes `“ ”` (from word processors or chats) are not YAML quotes and end up inside the value.

```yaml
action: tts.speak
target:
  entity_id: tts.silero_tts_enhanced
data:
  media_player_entity_id: media_player.living_room
  message: "Attention. The CPU temperature has reached 80 degrees."
  options:
    model_id: v5_5_ru
    voice: xenia
    put_accent: true
```

```yaml
action: tts.speak
target:
  entity_id: tts.silero_tts_enhanced
data:
  media_player_entity_id: media_player.living_room
  message: '<speak>Через 3 минуты<break time="2s"/> кофе будет готов.</speak>'
```

```yaml
action: tts.speak
target:
  entity_id: tts.silero_tts_enhanced
data:
  media_player_entity_id: media_player.living_room
  message: "Hello world, the smart home is ready."
  language: en
  options:
    model_id: v3_en
    voice: en_24
```

## ⏱ Speed
* Once a model is loaded, a short phrase is synthesized in a fraction of a second. On an Apple M4 Pro, measured through the container: 60 ms for a 3-second phrase, 130 ms for 7 seconds. Slower CPUs take several times longer.
* The first request after the add-on starts used to be the slow one, because the model had to load. The add-on now remembers the models you used (`/data/silero_cache/last_models.json`) and loads them in the background at startup.
* The sample rate (24000 vs 48000) does not change synthesis speed, only the size of the audio.
* The add-on log shows the time of every request, for example `синтез 0.12 с`, plus `загрузка модели` or `ожидание очереди` when they apply. If speech feels slow, compare these numbers with the delay you notice: the rest comes from Home Assistant and the media player.
* To time the add-on alone: `time curl -s -o /dev/null -X POST http://HOST:8014/tts -H 'Content-Type: application/json' -d '{"text":"Проверка скорости.","voice":"kseniya","language":"ru","model_id":"v5_5_ru"}'`

## ⚠️ Known limits
* "1" and "2" follow the next noun in the nominative and accusative only; dates like `1 января` are read as plain numbers.
* Latin words are transliterated letter by letter with a small dictionary of common words, so exotic names may sound approximate.
* Languages without number words in the library (`tt`, `ba`, `xal`) read numbers in Russian.

----------------------------------------------------------

# Silero TTS Enhanced Engine

Локальный, быстрый и качественный синтезатор речи для вашего Умного дома.

Этот аддон основан на нейросетевых моделях [Silero Models](https://github.com/snakers4/silero-models) и обёртке [silero-tts](https://github.com/daswer123/silero-tts-enhanced) от [daswer123](https://github.com/daswer123), дополненной собственной подготовкой текста.

## 🔥 Возможности
* **Работает локально:** Без облаков. Модели и список моделей Silero сохраняются в `/data`, поэтому после первой загрузки аддон работает и без интернета (если список обновить не удалось, берётся сохранённая копия).
* **Кэш в ОЗУ:** Держит несколько моделей загруженными одновременно, переключение между ними мгновенное. Количество задаётся на вкладке **Конфигурация** аддона (*Моделей в оперативной памяти*, по умолчанию 2, около 230 МБ каждая). Остальные модели подгружаются с диска.
* **Подготовка текста:**
  * числа читаются словами; по-русски «один» и «два» согласуются со следующим существительным (`1 час`, `21 минута`, `2 минуты`), у отрицательных чисел появляется «минус», длинные числа и коды вроде `007` читаются по цифрам;
  * латинские слова и аббревиатуры в русском тексте транслитерируются, иначе модель их пропускает (`Wi-Fi` → «вай-фай», `USB` → «ю эс би»);
  * длинные сообщения автоматически делятся на предложения.
* **SSML:** паузы, скорость и высота голоса (см. ниже).
* **Ударения:** Вы можете явно указать ударение в сложных словах, поставив знак `+` перед гласной (например: `зам+ок`).

## 🛠 Доступные модели и языки
Аддон скачивает любую модель, которую вы запросите из Интеграции, при первом обращении. При неизвестной модели, голосе или языке возвращается ошибка со списком допустимых значений.
Самые популярные:
* **Русский (ru):** `v5_5_ru` (голоса: aidar, baya, kseniya, xenia, eugene), `v5_ru`
* **Английский (en):** `v3_en` (голоса: en_0, en_1 ... en_117, random)
* **Украинский (ua):** `v4_ua` (голоса: mykyta, random)

Коды языков: `ru`, `en`, `ua`. Принимаются также `uk` из Home Assistant и формы с регионом вроде `ru-RU` или `en-US`. Для других программ: `GET /models` — модели по языкам, `GET /voices?model_id=v5_5_ru&language=ru` — голоса, `GET /status` — что загружено.

## ⚙️ Переключатели автоударения и Ё
Две галочки в настройках интеграции передаются как `put_accent` и `put_yo`, их можно переопределить для отдельного вызова в `options`.
* **Автоматическая расстановка ударений** (`put_accent`) — модель сама ставит ударения. Выключите, чтобы говорить без автоматических ударений; ударения, заданные через `+`, продолжают работать.
* **Автоматическая расстановка буквы Ё** (`put_yo`) — возвращает `ё` в словах, написанных через `е` (`елка` → `ёлка`).
* Неоднозначные слова (омографы вроде `замок`, `все`/`всё`) модель разбирает сама, эти два переключателя на них не влияют.

## 🎚 SSML
Оберните сообщение в `<speak>…</speak>` (модели v5). Поддерживаются теги: `<break time="3s"/>` (также `500ms`), `<prosody rate="slow" pitch="high">`, `<p>`, `<s>`.
Числа и латиница внутри текста обрабатываются как обычно, атрибуты тегов не затрагиваются. SSML-сообщение уходит в модель целиком, поэтому держите его до 1000 символов (более длинные отклоняются с понятной ошибкой; у обычного текста такого предела нет).

## 💡 Примеры автоматизаций
Используйте обычные прямые кавычки `'` и `"`. Типографские кавычки `“ ”` (из текстовых редакторов и мессенджеров) не являются кавычками YAML и попадают внутрь значения.

```yaml
action: tts.speak
target:
  entity_id: tts.silero_tts_enhanced
data:
  media_player_entity_id: media_player.living_room
  message: "Внимание. Температура процессора достигла 80 градусов."
  options:
    model_id: v5_5_ru
    voice: xenia
    put_accent: true
```

```yaml
action: tts.speak
target:
  entity_id: tts.silero_tts_enhanced
data:
  media_player_entity_id: media_player.living_room
  message: '<speak>Через 3 минуты<break time="2s"/> кофе будет готов.</speak>'
```

```yaml
action: tts.speak
target:
  entity_id: tts.silero_tts_enhanced
data:
  media_player_entity_id: media_player.living_room
  message: "Hello world, the smart home is ready."
  language: en
  options:
    model_id: v3_en
    voice: en_24
```

## ⏱ Скорость
* Когда модель загружена, короткая фраза синтезируется за доли секунды. На Apple M4 Pro, измерено через контейнер: 60 мс для 3-секундной фразы, 130 мс для 7-секундной. На более слабых процессорах — в несколько раз дольше.
* Раньше медленным был первый запрос после запуска аддона: модель нужно было загрузить. Теперь аддон запоминает использованные модели (`/data/silero_cache/last_models.json`) и при старте загружает их в фоне.
* Частота дискретизации (24000 или 48000) не влияет на скорость синтеза, только на размер аудио.
* В логе аддона время каждого запроса, например `синтез 0.12 с`, а при необходимости `загрузка модели` или `ожидание очереди`. Если речь кажется медленной, сравните эти цифры с задержкой, которую вы замечаете: остальное приходится на Home Assistant и медиаплеер.
* Замерить только аддон: `time curl -s -o /dev/null -X POST http://HOST:8014/tts -H 'Content-Type: application/json' -d '{"text":"Проверка скорости.","voice":"kseniya","language":"ru","model_id":"v5_5_ru"}'`

## ⚠️ Известные ограничения
* «Один» и «два» согласуются со следующим словом только в именительном и винительном падежах; даты вроде `1 января` читаются обычными числами.
* Латиница транслитерируется побуквенно с небольшим словарём частых слов, поэтому редкие названия могут звучать приблизительно.
* Языки без числительных в библиотеке (`tt`, `ba`, `xal`) читают числа по-русски.
