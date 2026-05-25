import requests


class OllamaCleanupError(RuntimeError):
    pass


class OllamaCleaner:
    def __init__(self, base_url: str, model: str, prompt: str, timeout_seconds: int = 45) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model.strip()
        self.prompt = prompt.strip()
        self.timeout_seconds = timeout_seconds

    def clean(self, text: str) -> str:
        original = text.strip()
        if not original:
            return original
        if not self.model:
            raise OllamaCleanupError("Ollama model name is empty.")

        payload = {
            "model": self.model,
            "prompt": f"{self.prompt}\n\nRaw dictation:\n{original}",
            "stream": False,
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError as exc:
            raise OllamaCleanupError("Ollama is not running. Start Ollama or disable local cleanup.") from exc
        except requests.exceptions.Timeout as exc:
            raise OllamaCleanupError("Ollama cleanup timed out. Try a smaller model or disable local cleanup.") from exc
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                raise OllamaCleanupError(
                    f"Ollama model '{self.model}' was not found. Run: ollama pull {self.model}"
                ) from exc
            raise OllamaCleanupError(f"Ollama cleanup failed: {exc}") from exc
        except requests.RequestException as exc:
            raise OllamaCleanupError(f"Ollama cleanup failed: {exc}") from exc

        data = response.json()
        cleaned = str(data.get("response", "")).strip()
        return cleaned or original
