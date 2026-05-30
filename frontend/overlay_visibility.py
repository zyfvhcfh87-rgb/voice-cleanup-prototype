OVERLAY_VISIBILITY_MODES = {"always", "active", "never"}
OVERLAY_ACTIVE_STATES = {
    "recording",
    "stopping",
    "processing",
    "transcribing",
    "cleaning",
    "inserting",
    "error",
}


def normalize_overlay_visibility_mode(mode: str | None) -> str:
    if mode in OVERLAY_VISIBILITY_MODES:
        return mode
    return "active"


def should_show_mic_overlay(mode: str | None, app_state: str) -> bool:
    normalized = normalize_overlay_visibility_mode(mode)
    if normalized == "always":
        return True
    if normalized == "never":
        return False
    return app_state in OVERLAY_ACTIVE_STATES
