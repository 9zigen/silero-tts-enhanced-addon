"""Подготовка текста для Silero: числа, латиница, SSML и разбиение на куски."""
import re
from functools import lru_cache

from number2text.number2text import NumberToText
from silero_tts.lang_data import is_cyrillic, is_latin, lang_data
from silero_tts.transliterate import reverse_transliterate, transliterate

# Модель падает на тексте длиннее ~1000 символов и сильно раздувает память на длинных кусках
MAX_CHUNK = 450

QUOTES = "\"'`“”„‟‘’‚«»"
SSML_TAG = re.compile(r"(<[^>]+>)")


def clean(value: str) -> str:
    # Умные кавычки и пробелы из полей интеграции HA ломают поиск модели в конфиге
    return value.strip().strip(QUOTES).strip()


LANGUAGE_ALIASES = {"uk": "ua"}  # украинский: uk в Home Assistant, ua у Silero


def normalize_language(value: str) -> str:
    # ru-RU, en_US, UK -> ru, en, ua
    code = clean(value).replace("_", "-").split("-")[0].lower()
    return LANGUAGE_ALIASES.get(code, code)


def extract_ssml(text: str):
    # SSML может прийти в кавычках из message автоматизации: “<speak>...</speak>"
    candidate = clean(text)
    lowered = candidate.lower()
    if lowered.startswith("<speak") and lowered.endswith("</speak>"):
        return candidate
    return None


# ---------------------------------------------------------------- числа

_ONES = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
_TEENS = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать",
          "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
_TENS = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят",
         "восемьдесят", "девяносто"]
_HUNDREDS = ["", "сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот", "семьсот",
             "восемьсот", "девятьсот"]
# (форма для 1, для 2-4, для 5+, род числительного перед ней)
_SCALES = [("тысяча", "тысячи", "тысяч", "f"),
           ("миллион", "миллиона", "миллионов", "m"),
           ("миллиард", "миллиарда", "миллиардов", "m")]
_ONE = {"m": "один", "f": "одна", "n": "одно", "a": "одну"}

# Языки без своих числительных в number2text читаются русскими
RU_LIKE = {"ru", "tt", "ba", "xal", "cyrillic"}
NUMBER_LANGUAGES = {"ua": "uk"}
MINUS = {"ru": "минус", "tt": "минус", "ba": "минус", "xal": "минус", "cyrillic": "минус",
         "ua": "мінус", "en": "minus", "de": "minus", "es": "menos", "fr": "moins"}

_FEM_SOFT = {"ночь", "дверь", "тень", "мышь"}
_NOT_NOUNS = {"и", "в", "на", "с", "по", "до", "от", "из", "за", "к", "у", "о", "а", "но",
              "или", "не", "же", "ли", "при", "для", "под", "над", "про"}
_NOUN = re.compile(r"\s*([А-Яа-яЁё+]+)")


def _plural(n, one, few, many):
    if 11 <= n % 100 <= 14:
        return many
    if n % 10 == 1:
        return one
    if 2 <= n % 10 <= 4:
        return few
    return many


def _ru_group(n, gender):
    words = [_HUNDREDS[n // 100]]
    rest = n % 100
    if 10 <= rest < 20:
        words.append(_TEENS[rest - 10])
    else:
        words.append(_TENS[rest // 10])
        unit = rest % 10
        if unit == 1:
            words.append(_ONE[gender])
        elif unit == 2:
            words.append("две" if gender in ("f", "a") else "два")
        else:
            words.append(_ONES[unit])
    return [w for w in words if w]


def ru_number(n: int, gender: str = "m") -> str:
    """Число прописью, до 999 999 999 999. gender: m, f, n или a (винительный женского: «одну»)."""
    if n == 0:
        return "ноль"
    groups = []
    while n:
        groups.append(n % 1000)
        n //= 1000
    words = []
    for i in range(len(groups) - 1, -1, -1):
        value = groups[i]
        if not value:
            continue
        if i == 0:
            words += _ru_group(value, gender)
        else:
            one, few, many, scale_gender = _SCALES[i - 1]
            words += _ru_group(value, scale_gender)
            words.append(_plural(value, one, few, many))
    return " ".join(words)


def ru_gender(number: int, tail: str) -> str:
    """Род для «один/два» по слову, которое идёт за числом (именительный и винительный падежи)."""
    unit = number % 10
    if unit not in (1, 2) or 11 <= number % 100 <= 14:
        return "m"
    match = _NOUN.match(tail)
    if not match:
        return "m"
    word = match.group(1).lower().replace("+", "")
    if len(word) < 3 or word in _NOT_NOUNS:
        return "m"
    last = word[-1]
    if unit == 1:
        if word in _FEM_SOFT or last in "ая":
            return "f"
        if last in "ую":
            return "a"
        if last in "оеё":
            return "n"
        return "m"
    return "f" if last in "ыи" else "m"


@lru_cache(maxsize=None)
def number_converter(language: str):
    """Фабрика вместо NumberToText: библиотека падает на языках без числительных (ua, tt, ...)."""
    language = NUMBER_LANGUAGES.get(language, language)
    try:
        return NumberToText(language)
    except ValueError:
        fallback = "ru" if language in RU_LIKE or lang_data.get(language, {}).get("script") == "cyrillic" else "en"
        print(f"Нет числительных для языка {language!r}, используется {fallback!r}")
        return NumberToText(fallback)


def _say(n: int, language: str, tail: str = "") -> str:
    if language in RU_LIKE:
        return ru_number(n, ru_gender(n, tail))
    return number_converter(language).convert(n)


def spell_numbers(text: str, language: str) -> str:
    minus = MINUS.get(language)
    if minus:
        text = re.sub(r"(?<!\w)[-−](?=\d)", minus + " ", text)

    def replace(match):
        digits = match.group()
        if len(digits) > 12 or (len(digits) > 2 and digits[0] == "0"):
            # Номера и очень длинные числа читаем по цифрам
            return " ".join(_say(int(d), language) for d in digits)
        return _say(int(digits), language, text[match.end():])

    return re.sub(r"[0-9]+", replace, text)


# ---------------------------------------------------------------- латиница

_LATIN_WORD = re.compile(r"[A-Za-z]+(?:[-'’][A-Za-z]+)*")

_RU_WORDS = {
    "wi-fi": "вай-фай", "wifi": "вай-фай", "bluetooth": "блютус", "zigbee": "зигби",
    "z-wave": "зет-вэйв", "zwave": "зет-вэйв", "led": "лэд", "ram": "рэм", "lan": "лан",
    "home": "хоум", "assistant": "ассистент", "google": "гугл", "youtube": "ютуб",
    "netflix": "нетфликс", "spotify": "спотифай", "iphone": "айфон", "android": "андроид",
    "online": "онлайн", "offline": "офлайн", "ok": "окей", "okay": "окей",
}
_LETTER_NAMES = {
    "a": "эй", "b": "би", "c": "си", "d": "ди", "e": "и", "f": "эф", "g": "джи", "h": "эйч",
    "i": "ай", "j": "джей", "k": "кей", "l": "эл", "m": "эм", "n": "эн", "o": "оу", "p": "пи",
    "q": "кью", "r": "ар", "s": "эс", "t": "ти", "u": "ю", "v": "ви", "w": "дабл-ю", "x": "экс",
    "y": "вай", "z": "зед",
}
_TRIGRAPHS = {"sch": "ск", "tch": "ч", "igh": "ай"}
_DIGRAPHS = {"sh": "ш", "ch": "ч", "zh": "ж", "kh": "х", "ts": "ц", "ph": "ф", "th": "т",
             "ck": "к", "qu": "кв", "ee": "и", "oo": "у", "ea": "и"}
_SINGLES = {
    "a": "а", "b": "б", "c": "к", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "х", "i": "и",
    "j": "дж", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о", "p": "п", "q": "к", "r": "р",
    "s": "с", "t": "т", "u": "у", "v": "в", "w": "в", "x": "кс", "y": "и", "z": "з",
}


def _latin_part_to_ru(word: str) -> str:
    lowered = word.lower()
    if lowered in _RU_WORDS:
        result = _RU_WORDS[lowered]
    elif word.isupper() and 2 <= len(word) <= 5:
        # Аббревиатуры (USB, MQTT, CPU) читаем по буквам
        return " ".join(_LETTER_NAMES[c] for c in lowered)
    else:
        result = _translit_latin(lowered)
    if word.isupper() and len(word) > 1:
        return result
    return result[:1].upper() + result[1:] if word[:1].isupper() else result


def _translit_latin(word: str) -> str:
    out = []
    i = 0
    while i < len(word):
        for size in (3, 2):
            chunk = word[i:i + size]
            table = _TRIGRAPHS if size == 3 else _DIGRAPHS
            if len(chunk) == size and chunk in table:
                out.append(table[chunk])
                i += size
                break
        else:
            char = word[i]
            if char == "c":
                out.append("с" if word[i + 1:i + 2] in ("e", "i", "y") else "к")
            elif char == "y":
                out.append("й" if i == 0 or word[i - 1] in "aeiou" else "и")
            elif char == "e" and i == len(word) - 1 and i >= 3 and word[i - 1] not in "aeiouy":
                pass  # немое e на конце: phone -> фон
            else:
                out.append(_SINGLES[char])
            i += 1
    return "".join(out)


def latin_to_ru(word: str) -> str:
    if word.lower() in _RU_WORDS:
        return _latin_part_to_ru(word)
    parts = re.split(r"([-'’])", word)
    return "".join("" if p in ("'", "’") else p if p == "-" else _latin_part_to_ru(p) for p in parts)


def transliterate_text(text: str, language: str) -> str:
    if language == "ru":
        def replace(match):
            suffix = " " if match.end() < len(text) and text[match.end()].isdigit() else ""
            return latin_to_ru(match.group()) + suffix
        return _LATIN_WORD.sub(replace, text)

    # Остальные языки — как в библиотеке: целиком, только если весь текст в чужом алфавите
    script = lang_data.get(language, {}).get("script")
    try:
        if script == "cyrillic" and is_latin(text):
            return reverse_transliterate(text, language)
        if script == "latin" and is_cyrillic(text):
            if language in ("en", "fr", "es", "de"):
                return reverse_transliterate(text, language)
            return transliterate(text, language)
    except ValueError:
        pass
    return text


# ---------------------------------------------------------------- сборка

def prepare_text(text: str, language: str) -> str:
    """Правила для обычного текста (не для тегов SSML)."""
    text = transliterate_text(text, language)
    rules = lang_data.get(language, {})
    for old, new in rules.get("replacements", []):
        text = text.replace(old, new)
    for pattern, replacement in rules.get("patterns", []):
        text = re.sub(pattern, replacement, text)
    return spell_numbers(text, language)


def prepare_ssml(ssml: str, language: str) -> str:
    # Правила применяем только к тексту между тегами: атрибуты (time="3s") трогать нельзя
    parts = SSML_TAG.split(ssml)
    parts[0::2] = [prepare_text(p, language) if p.strip() else p for p in parts[0::2]]
    return "".join(parts)


def _pack(pieces, limit):
    chunks, current = [], ""
    for piece in pieces:
        if current and len(current) + 1 + len(piece) > limit:
            chunks.append(current)
            current = piece
        else:
            current = f"{current} {piece}" if current else piece
    if current:
        chunks.append(current)
    return chunks


def _split_line(line, limit):
    if len(line) <= limit:
        return [line]
    pieces = []
    for sentence in re.split(r"(?<=[.!?…])\s+", line):
        if len(sentence) <= limit:
            pieces.append(sentence)
            continue
        for clause in re.split(r"(?<=[,;:])\s+", sentence):
            if len(clause) <= limit:
                pieces.append(clause)
                continue
            for word in clause.split():
                pieces += [word[i:i + limit] for i in range(0, len(word), limit)]
    return _pack(pieces, limit)


def split_chunks(text: str, limit: int = MAX_CHUNK):
    """Строки текста, длинные строки режутся по предложениям, затем по запятым и пробелам."""
    chunks = []
    for line in text.split("\n"):
        line = line.strip()
        if line:
            chunks += _split_line(line, limit)
    return chunks
