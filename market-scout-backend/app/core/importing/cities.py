import re

_NOISE = re.compile(r"[^a-z0-9 ]+")
_SUFFIXES = (" city", " district", " cantt", " cantonment")


def _plain(text: str) -> str:
    cleaned = _NOISE.sub(" ", text.lower())
    cleaned = " ".join(cleaned.split())
    for suffix in _SUFFIXES:
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)]
    return cleaned


class CityMatcher:
    def __init__(self, cities: dict[str, int]) -> None:
        self._by_plain = {_plain(name): city_id for name, city_id in cities.items()}
        names = sorted(self._by_plain, key=len, reverse=True)
        self._in_text = re.compile(r"\b(" + "|".join(re.escape(n) for n in names) + r")\b") if names else None

    def from_city_text(self, text: str | None) -> int | None:
        return self._by_plain.get(_plain(text)) if text else None

    def from_address(self, address: str | None) -> int | None:
        if not address or self._in_text is None:
            return None
        found = self._in_text.findall(_plain(address))
        return self._by_plain[found[-1]] if found else None
