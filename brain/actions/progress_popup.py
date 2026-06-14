import threading
import tkinter as tk
from tkinter import ttk

from utils.logger import setup_logger
logger = setup_logger(__name__)


class ProgressPopup:
    def __init__(self, title="Progress", message="Processing..."):
        self._cancelled = False
        self._popup = None
        self._progress_bar = None
        self._status_label = None
        self._cancel_button = None
        self._after_id = None

        self._ready = threading.Event()
        self._thread = threading.Thread(
            target=self._run_tk, args=(title, message), daemon=True
        )
        self._thread.start()
        self._ready.wait(timeout=5)

    def _run_tk(self, title: str, message: str):
        root = tk.Tk()
        root.withdraw()

        popup = tk.Toplevel(root)
        popup.title(title)
        popup.resizable(False, False)
        popup.grab_set()
        popup.protocol("WM_DELETE_WINDOW", self._cancel)

        status_label = ttk.Label(popup, text=message, font=("Arial", 10))
        status_label.pack(pady=15, padx=25)

        progress_bar = ttk.Progressbar(
            popup, orient="horizontal", length=300, mode="determinate"
        )
        progress_bar.pack(pady=5, padx=25)

        cancel_button = ttk.Button(popup, text="Cancel", command=self._cancel)
        cancel_button.pack(pady=15)

        popup.update_idletasks()
        pw = popup.winfo_reqwidth()
        ph = popup.winfo_reqheight()
        sw = popup.winfo_screenwidth()
        sh = popup.winfo_screenheight()
        x = (sw - pw) // 2
        y = (sh - ph) // 2
        popup.geometry(f"+{x}+{y}")

        self._popup = popup
        self._status_label = status_label
        self._progress_bar = progress_bar
        self._cancel_button = cancel_button
        self._ready.set()

        root.mainloop()

    def _cancel(self):
        self._cancelled = True
        if self._after_id:
            self._popup.after_cancel(self._after_id)
        if self._popup:
            self._status_label.config(text="Cancelled")
            self._cancel_button.config(text="Close", command=self._destroy)
            self._popup.after(500, self._destroy)

    def _destroy(self):
        if self._popup:
            try:
                self._popup.destroy()
            except Exception:
                pass
            self._popup = None

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def update(self, percent: int, status: str = None):
        if not self._popup or self._cancelled:
            return
        def _do():
            if self._progress_bar:
                self._progress_bar["value"] = percent
            if status and self._status_label:
                self._status_label.config(text=status)
        try:
            self._popup.after(0, _do)
        except Exception:
            pass

    def close(self):
        self._popup.after(0, self._destroy)
