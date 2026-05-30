from dataclasses import asdict, dataclass
from datetime import date
import json
import re

from config.settings import APP_DIR


STATS_FILE = APP_DIR / "dictation_stats.json"


@dataclass
class DictationStats:
    day: str
    sessions: int = 0
    words: int = 0

    @property
    def minutes_saved(self) -> int:
        return round(self.words / 40)


def load_today_stats() -> DictationStats:
    today = date.today().isoformat()
    if not STATS_FILE.exists():
        return DictationStats(day=today)

    try:
        data = json.loads(STATS_FILE.read_text(encoding="utf-8"))
        stats = DictationStats(**data)
        if stats.day != today:
            return DictationStats(day=today)
        return stats
    except Exception:
        return DictationStats(day=today)


def save_stats(stats: DictationStats) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    STATS_FILE.write_text(json.dumps(asdict(stats), indent=2), encoding="utf-8")


def record_dictation_session(text: str) -> DictationStats:
    stats = load_today_stats()
    stats.sessions += 1
    stats.words += len(re.findall(r"\b[\w']+\b", text))
    save_stats(stats)
    return stats
