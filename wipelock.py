import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

from pynput import keyboard, mouse

APP_NAME = "WipeLock"
UNLOCK_HOTKEY = "Ctrl + Alt + W"


class WipeLockApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("760x500")
        self.root.minsize(620, 430)
        self.root.configure(bg="#0b0f14")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.locked = False
        self.remaining = 0
        self.lock_thread = None
        self.keyboard_listener = None
        self.mouse_listener = None
        self.stop_event = threading.Event()

        self._build_ui()
        self.root.after(200, self._tick_ui)

    def _build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", padding=8)
        style.configure("TButton", padding=10, font=("Segoe UI", 10, "bold"))

        header = tk.Frame(self.root, bg="#0b0f14")
        header.pack(fill="x", padx=36, pady=(30, 0))

        tk.Label(header, text="WIPELOCK", font=("Segoe UI", 24, "bold"),
                 fg="#f4f7fb", bg="#0b0f14").pack(side="left")
        tk.Label(header, text="Safe input lock", font=("Segoe UI", 10),
                 fg="#8e9aaa", bg="#0b0f14").pack(side="left", padx=12, pady=(8, 0))

        card = tk.Frame(self.root, bg="#121821", highlightbackground="#202b38", highlightthickness=1)
        card.pack(fill="both", expand=True, padx=36, pady=28)

        self.status = tk.Label(card, text="Ready", font=("Segoe UI", 12, "bold"),
                               fg="#79e6a0", bg="#121821")
        self.status.pack(pady=(30, 8))

        self.timer_label = tk.Label(card, text="00:00", font=("Segoe UI", 62, "bold"),
                                    fg="#f4f7fb", bg="#121821")
        self.timer_label.pack(pady=8)

        controls = tk.Frame(card, bg="#121821")
        controls.pack(pady=12)
        tk.Label(controls, text="Lock duration", font=("Segoe UI", 10),
                 fg="#aeb9c7", bg="#121821").pack(side="left", padx=(0, 10))

        self.duration_var = tk.StringVar(value="30 seconds")
        self.duration_box = ttk.Combobox(
            controls,
            textvariable=self.duration_var,
            values=("10 seconds", "30 seconds", "60 seconds", "2 minutes", "5 minutes"),
            state="readonly",
            width=16,
        )
        self.duration_box.pack(side="left")

        self.lock_button = ttk.Button(card, text="Start WipeLock", command=self.start_lock)
        self.lock_button.pack(pady=18)

        self.help_label = tk.Label(
            card,
            text=f"Emergency unlock: {UNLOCK_HOTKEY}  •  The timer also unlocks automatically.",
            font=("Segoe UI", 9), fg="#8e9aaa", bg="#121821"
        )
        self.help_label.pack(pady=(2, 24))

        footer = tk.Label(self.root,
                          text="WipeLock is a local Windows utility. Keep the emergency hotkey available.",
                          font=("Segoe UI", 8), fg="#687586", bg="#0b0f14")
        footer.pack(pady=(0, 18))

    def _duration_seconds(self):
        text = self.duration_var.get()
        number = int(text.split()[0])
        if "minute" in text:
            return number * 60
        return number

    def start_lock(self):
        if self.locked:
            return

        seconds = self._duration_seconds()
        self.remaining = seconds
        self.locked = True
        self.stop_event.clear()
        self.lock_button.configure(state="disabled")
        self.duration_box.configure(state="disabled")
        self.status.configure(text="LOCKED — input is blocked", fg="#ffb86b")
        confirmed = messagebox.askyesno(
            APP_NAME,
            f"Lock keyboard and mouse for {seconds} seconds?\n\n"
            f"Emergency unlock: {UNLOCK_HOTKEY}\n"
            "The timer will unlock automatically.",
            parent=self.root,
        )
        if not confirmed:
            self.locked = False
            self.remaining = 0
            return

        self._set_locked_window(True)
        try:
            self._start_input_blockers()
        except Exception as exc:
            self._stop_input_blockers()
            self.locked = False
            self.remaining = 0
            self._set_locked_window(False)
            self.lock_button.configure(state="normal")
            self.duration_box.configure(state="readonly")
            self.status.configure(text="Could not start input lock", fg="#ff7777")
            messagebox.showerror(APP_NAME, f"Could not start input lock:\n{exc}", parent=self.root)
            return

        self.lock_thread = threading.Thread(target=self._countdown, daemon=True)
        self.lock_thread.start()

    def _start_input_blockers(self):
        self._hotkey = keyboard.HotKey(
            keyboard.HotKey.parse("<ctrl>+<alt>+w"),
            self.unlock,
        )

        # Keep the emergency shortcut active while suppressing ordinary input.
        def on_press(key):
            self._hotkey.press(self._hotkey_listener.canonical(key))

        def on_release(key):
            self._hotkey.release(self._hotkey_listener.canonical(key))

        self._hotkey_listener = keyboard.Listener(
            on_press=on_press,
            on_release=on_release,
            suppress=True,
        )
        self._hotkey_listener.start()

        # suppress=True blocks mouse input; callbacks must not return False,
        # because False would stop the listener after the first mouse event.
        self.mouse_listener = mouse.Listener(
            on_move=lambda x, y: None,
            on_click=lambda x, y, button, pressed: None,
            on_scroll=lambda x, y, dx, dy: None,
            suppress=True,
        )
        self.mouse_listener.start()

    def _countdown(self):
        while self.remaining > 0 and not self.stop_event.is_set():
            time.sleep(1)
            self.remaining -= 1
        if not self.stop_event.is_set():
            self.root.after(0, self.unlock)

    def unlock(self):
        if not self.locked:
            return
        self.stop_event.set()
        self._stop_input_blockers()
        self.locked = False
        self.remaining = 0
        self.root.after(0, self._reset_ui)

    def _stop_input_blockers(self):
        for listener in (self._hotkey_listener, self.mouse_listener):
            try:
                if listener is not None:
                    listener.stop()
            except Exception:
                pass
        self._hotkey_listener = None
        self.mouse_listener = None

    def _reset_ui(self):
        self.lock_button.configure(state="normal")
        self.duration_box.configure(state="readonly")
        self.status.configure(text="Ready", fg="#79e6a0")
        self._set_locked_window(False)

    def _set_locked_window(self, locked):
        try:
            self.root.attributes("-topmost", locked)
            if locked:
                self.root.attributes("-fullscreen", True)
            else:
                self.root.attributes("-fullscreen", False)
        except tk.TclError:
            pass

    def _tick_ui(self):
        mins, secs = divmod(max(0, self.remaining), 60)
        self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")
        self.root.after(200, self._tick_ui)

    def on_close(self):
        if self.locked:
            messagebox.showwarning(
                APP_NAME,
                f"Unlock first with {UNLOCK_HOTKEY}.\n\nThe timer will also unlock automatically.",
                parent=self.root,
            )
            return
        self._stop_input_blockers()
        self.root.destroy()


def main():
    root = tk.Tk()
    WipeLockApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
