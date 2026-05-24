import re


class RuleBasedCleaner:
    def __init__(self, prompt: str = "") -> None:
        self.prompt = prompt

    def clean(self, text: str) -> str:
        cleaned = text.strip()
        cleaned = self._remove_common_whisper_markers(cleaned)
        cleaned = self._normalize_spacing(cleaned)
        cleaned = self._remove_repeated_fillers(cleaned)
        cleaned = self._capitalize_sentences(cleaned)
        return cleaned

    def _remove_common_whisper_markers(self, text: str) -> str:
        return re.sub(r"\[(music|applause|laughter|noise|silence)\]", "", text, flags=re.IGNORECASE)

    def _normalize_spacing(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\s+([,.!?;:])", r"\1", text)
        text = re.sub(r"([,.!?;:])([^\s])", r"\1 \2", text)
        return text.strip()

    def _remove_repeated_fillers(self, text: str) -> str:
        fillers = r"\b(um+|uh+|erm|like|you know)\b"
        text = re.sub(rf"({fillers}[, ]*){{2,}}", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _capitalize_sentences(self, text: str) -> str:
        if not text:
            return text

        parts = re.split(r"([.!?]\s+)", text)
        capitalized: list[str] = []
        for part in parts:
            if part and not re.match(r"[.!?]\s+", part):
                part = part[0].upper() + part[1:]
            capitalized.append(part)
        return "".join(capitalized)
