from dataclasses import asdict, dataclass
from datetime import date
import json
import re
from collections import Counter

from config.settings import APP_DIR


STATS_FILE = APP_DIR / "dictation_stats.json"


@dataclass
class DictationStats:
    day: str
    sessions: int = 0
    words: int = 0
    sessions_list: list = None

    @property
    def minutes_saved(self) -> int:
        return round(self.words / 40)


def load_today_stats() -> DictationStats:
    today = date.today().isoformat()
    if not STATS_FILE.exists():
        return DictationStats(day=today, sessions_list=[])

    try:
        data = json.loads(STATS_FILE.read_text(encoding="utf-8"))
        # Clean data to only include valid fields for dataclass instantiation
        valid_fields = {"day", "sessions", "words", "sessions_list"}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        stats = DictationStats(**filtered_data)
        if stats.day != today:
            return DictationStats(day=today, sessions_list=[])
        if stats.sessions_list is None:
            stats.sessions_list = []
        return stats
    except Exception:
        return DictationStats(day=today, sessions_list=[])


def save_stats(stats: DictationStats) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    STATS_FILE.write_text(json.dumps(asdict(stats), indent=2), encoding="utf-8")


def record_dictation_session(text: str, duration_seconds: float = 0.0, microphone: str = "Unknown Mic") -> DictationStats:
    stats = load_today_stats()
    if stats.sessions_list is None:
        stats.sessions_list = []
    
    words_count = len(re.findall(r"\b[\w']+\b", text))
    stats.sessions_list.append({
        "words": words_count,
        "duration_seconds": duration_seconds,
        "microphone": microphone
    })
    stats.sessions = len(stats.sessions_list)
    stats.words = sum(s["words"] for s in stats.sessions_list)
    save_stats(stats)
    return stats


def get_most_used_mic(stats: DictationStats) -> tuple[str, float]:
    """Returns (microphone_name, percentage_of_sessions)"""
    if not stats.sessions_list:
        return ("No Microphone", 0.0)
    
    mics = [s.get("microphone", "Unknown Mic") for s in stats.sessions_list]
    counts = Counter(mics)
    if not counts:
        return ("No Microphone", 0.0)
    
    most_common_mic, count = counts.most_common(1)[0]
    percentage = (count / len(stats.sessions_list)) * 100.0
    return (most_common_mic, percentage)


def get_avg_session_length(stats: DictationStats) -> float:
    """Returns average session length in seconds"""
    if not stats.sessions_list:
        return 0.0
    durations = [s.get("duration_seconds", 0.0) for s in stats.sessions_list]
    return sum(durations) / len(stats.sessions_list)
