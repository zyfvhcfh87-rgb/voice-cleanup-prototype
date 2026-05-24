from PySide6.QtCore import QObject, Signal

from audio.recorder import log_event


class PushToTalkHotkeyController(QObject):
    pressed = Signal()
    released = Signal()
    error = Signal(str)

    HOTKEYS = {
        "ctrl_win": {"ctrl", "win"},
        "ctrl_alt": {"ctrl", "alt"},
        "ctrl_shift_space": {"ctrl", "shift", "space"},
    }

    def __init__(self) -> None:
        super().__init__()
        self.hotkey_choice = "ctrl_win"
        self.enabled = True
        self._pressed_keys: set[str] = set()
        self._shortcut_active = False
        self._listener = None

    def start(self) -> None:
        if self._listener is not None:
            return
        try:
            from pynput import keyboard

            self._keyboard = keyboard
            self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
            self._listener.daemon = True
            self._listener.start()
            log_event("push_to_talk listener started")
        except Exception as exc:
            log_event(f"push_to_talk listener failed: {repr(exc)}")
            self.error.emit(str(exc))

    def stop(self) -> None:
        if self._listener is None:
            return
        self._listener.stop()
        self._listener = None
        log_event("push_to_talk listener stopped")

    def configure(self, enabled: bool, hotkey_choice: str) -> None:
        self.enabled = enabled
        self.hotkey_choice = hotkey_choice if hotkey_choice in self.HOTKEYS else "ctrl_win"
        self._pressed_keys.clear()
        self._shortcut_active = False
        log_event(f"push_to_talk configured enabled={enabled} hotkey={self.hotkey_choice}")

    def _on_press(self, key) -> None:
        if not self.enabled:
            return
        key_name = self._key_name(key)
        if key_name is None:
            return
        self._pressed_keys.add(key_name)
        required = self.HOTKEYS[self.hotkey_choice]
        if required.issubset(self._pressed_keys) and not self._shortcut_active:
            self._shortcut_active = True
            log_event(f"hotkey pressed: {self.hotkey_choice}")
            self.pressed.emit()

    def _on_release(self, key) -> None:
        key_name = self._key_name(key)
        if key_name is None:
            return
        self._pressed_keys.discard(key_name)
        required = self.HOTKEYS[self.hotkey_choice]
        if self._shortcut_active and not required.issubset(self._pressed_keys):
            self._shortcut_active = False
            log_event(f"hotkey released: {self.hotkey_choice}")
            self.released.emit()

    def _key_name(self, key) -> str | None:
        keyboard = self._keyboard
        if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            return "ctrl"
        if key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
            return "win"
        if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
            return "alt"
        if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
            return "shift"
        if key == keyboard.Key.space:
            return "space"
        return None
