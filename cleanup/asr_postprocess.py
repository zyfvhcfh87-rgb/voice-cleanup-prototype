import re


class ASRPostProcessor:
    """Conservative cleanup for Whisper-style ASR output.

    This cleaner is intentionally not a chatbot. It only removes obvious ASR
    noise, restores light punctuation/capitalization, and keeps the user's
    original words and meaning intact.
    """

    def clean(self, text: str) -> str:
        cleaned = text.strip()
        if not cleaned:
            return cleaned

        cleaned = self._remove_whisper_markers(cleaned)
        cleaned = self._normalize_spacing(cleaned)
        cleaned = self._remove_fillers(cleaned)
        cleaned = self._remove_accidental_repeats(cleaned)
        cleaned = self._restore_light_punctuation(cleaned)
        cleaned = self._capitalize_sentences(cleaned)
        cleaned = self._capitalize_standalone_i(cleaned)
        return cleaned.strip()

    def _remove_whisper_markers(self, text: str) -> str:
        return re.sub(r"\[(music|applause|laughter|noise|silence)\]", "", text, flags=re.IGNORECASE)

    def _normalize_spacing(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\s+([,.!?;:])", r"\1", text)
        text = re.sub(r"([,.!?;:])([^\s])", r"\1 \2", text)
        return text.strip()

    def _remove_fillers(self, text: str) -> str:
        # Keep this conservative so slang and casual wording survive.
        filler_patterns = [
            r"\b(?:um+|uh+|erm+|ah+|hmm+)\b[,\s]*",
            r"\b(?:you know|I mean)\b[,\s]*(?=(?:I|we|they|he|she|it|this|that|the|a|an)\b)",
            r"^(?:like|so)[,\s]+(?=\w)",
        ]
        for pattern in filler_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        return self._normalize_spacing(text)

    def _remove_accidental_repeats(self, text: str) -> str:
        # Remove immediate repeated words: "the the idea" -> "the idea".
        text = re.sub(r"\b(\w+)(\s+\1\b)+", r"\1", text, flags=re.IGNORECASE)

        # Remove immediate repeated short phrases up to three words.
        phrase_pattern = re.compile(
            r"\b(\w+(?:\s+\w+){0,2})(?:\s+\1\b)+",
            flags=re.IGNORECASE,
        )
        previous = None
        while previous != text:
            previous = text
            text = phrase_pattern.sub(r"\1", text)
        return self._normalize_spacing(text)

    def _restore_light_punctuation(self, text: str) -> str:
        if re.search(r"[.!?]$", text):
            return self._normalize_spacing(text)

        words = text.split()
        if not words:
            return text

        first_word = re.sub(r"^\W+|\W+$", "", words[0]).lower()
        question_starters = {
            "who",
            "what",
            "when",
            "where",
            "why",
            "how",
            "can",
            "could",
            "would",
            "should",
            "do",
            "does",
            "did",
            "is",
            "are",
            "am",
            "was",
            "were",
        }
        if first_word in question_starters:
            return f"{text}?"
        return f"{text}."

    def _capitalize_sentences(self, text: str) -> str:
        if not text:
            return text

        parts = re.split(r"([.!?]\s*)", text)
        output: list[str] = []
        capitalize_next = True
        for part in parts:
            if not part:
                continue
            if re.fullmatch(r"[.!?]\s*", part):
                output.append(part)
                capitalize_next = True
                continue
            if capitalize_next:
                part = part[0].upper() + part[1:]
                capitalize_next = False
            output.append(part)
        return "".join(output)

    def _capitalize_standalone_i(self, text: str) -> str:
        return re.sub(r"\bi\b", "I", text)
