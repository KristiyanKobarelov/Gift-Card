from datetime import datetime, timedelta
from Functions.check_existing import check_existing_code

# Basic Bulgarian (Cyrillic) -> Latin transliteration suitable for initials.
# Note: for initials we only need the first Latin letter, but we transliterate
# the whole string to handle cases like "Ж" -> "Zh" (initial becomes "Z").
_BG_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e",
    "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l",
    "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s",
    "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "c",
    "ш": "s", "щ": "s", "ъ": "a", "ь": "",
    "ю": "j", "я": "q",
}


def _translit_bg_to_lat(text: str) -> str:
    """Transliterate Bulgarian Cyrillic to Latin and FORCE UPPERCASE."""
    out: list[str] = []
    for ch in (text or "").strip():
        low = ch.lower()
        if low in _BG_TO_LAT:
            out.append(_BG_TO_LAT[low].upper())
        elif "A" <= ch <= "Z" or "a" <= ch <= "z":
            out.append(ch.upper())
        else:
            # ignore everything else (digits, symbols, spaces)
            pass
    return "".join(out)


def _latin_initial(name: str) -> str:
    """Return the first A-Z initial after transliteration. Fallback to 'X'."""
    lat = _translit_bg_to_lat(name)
    return lat[0] if lat else "X"


def create_code(sheet, firstname: str, lastname: str) -> str:
    # Initials must be in English alphabet even if input is Bulgarian.
    first_initial = _latin_initial(firstname)
    last_initial = _latin_initial(lastname)

    # Your existing rule: date + 1 year in ddmmyy format
    future_date = datetime.now() + timedelta(days=365)
    date_time = future_date.strftime("%d%m%y")

    # Try CR, then CM, then CT if collisions exist
    for prefix in ("CR", "CM", "CT"):
        code = f"{prefix}{date_time}{first_initial}{last_initial}"
        if not check_existing_code(sheet, code):
            return code

    # Extremely unlikely: all 3 prefixes already used for same date+initials.
    # Return the last attempted code.
    return code