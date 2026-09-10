#!/usr/bin/env python3
"""Stribe - audio to text, on your machine.

A desktop front end for OpenAI Whisper, dressed in the Stargit Solutions
design system. Everything runs locally; no audio ever leaves the machine.
"""
from __future__ import annotations

import ctypes
import os
import queue
import sys
import threading
import time
import traceback
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent

# pythonw.exe gives the process no console, so sys.stdout/stderr are None.
# Hand anything that writes to them somewhere harmless to go.
for _stream in ("stdout", "stderr"):
    if getattr(sys, _stream) is None:
        setattr(sys, _stream, open(os.devnull, "w", encoding="utf-8"))

# Whisper shells out to ffmpeg; make the bundled copy findable.
if (APP_DIR / "ffmpeg.exe").exists():
    os.environ["PATH"] = str(APP_DIR) + os.pathsep + os.environ.get("PATH", "")

import tkinter as tk                                          # noqa: E402
from tkinter import filedialog, font as tkfont, messagebox    # noqa: E402

from PIL import Image, ImageOps, ImageTk                      # noqa: E402

import theme as T                                             # noqa: E402
import widgets as W                                           # noqa: E402

APP_NAME = "Stribe"
APP_ID = "StargitSolutions.Stribe"     # taskbar identity, see _claim_app_identity
VERSION = "1.0.0"
TAGLINE = "Audio to text, entirely on your machine"

AUDIO_TYPES = [
    ("Audio & video", "*.mp3 *.wav *.m4a *.ogg *.oga *.opus *.flac *.aac *.wma "
                      "*.mp4 *.mkv *.mov *.avi *.webm"),
    ("MP3", "*.mp3"), ("WAV", "*.wav"), ("M4A", "*.m4a"),
    ("OGG / Opus", "*.ogg *.oga *.opus"), ("FLAC", "*.flac"),
    ("All files", "*.*"),
]

MODELS = [
    ("tiny", "Fastest. Good for a quick gist."),
    ("base", "Fast and accurate enough for most recordings."),
    ("small", "Slower, noticeably sharper on accents and names."),
    ("medium", "Slow, very accurate. Worth it for long interviews."),
    ("large", "Slowest and best. Downloads ~3 GB the first time."),
]
MODEL_HINTS = dict(MODELS)

LANGUAGES = [
    ("Detect automatically", None), ("English", "en"), ("French", "fr"),
    ("Spanish", "es"), ("German", "de"), ("Italian", "it"),
    ("Portuguese", "pt"), ("Dutch", "nl"), ("Polish", "pl"),
    ("Russian", "ru"), ("Arabic", "ar"), ("Hindi", "hi"),
    ("Chinese", "zh"), ("Japanese", "ja"), ("Korean", "ko"),
]
LANGUAGE_CODES = dict(LANGUAGES)


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


# =============================================================================
class Header(tk.Canvas):
    """Brand bar: generated nebula backdrop, logo mark and wordmark."""

    HEIGHT = 92

    def __init__(self, master):
        super().__init__(master, bg=T.BG, highlightthickness=0, bd=0,
                         height=T.px(self.HEIGHT), takefocus=0)
        self._source = Image.open(T.ASSETS / "hero.png").convert("RGB")
        self._backdrop: ImageTk.PhotoImage | None = None
        self._bg_item = self.create_image(0, 0, anchor="nw")
        self._width = 0
        self._resize_job: str | None = None

        mark = Image.open(T.ASSETS / "logo.png").resize(
            (T.px(46), T.px(46)), Image.LANCZOS)
        self._mark = ImageTk.PhotoImage(mark)

        pad = T.px(26)
        self.create_image(pad, T.px(self.HEIGHT) // 2, anchor="w", image=self._mark)

        text_x = pad + T.px(58)
        self.create_text(
            text_x, T.px(self.HEIGHT) // 2 - T.px(11), anchor="w", text=APP_NAME,
            fill=T.TEXT_HEADING, font=(T.DISPLAY, 21),
        )
        self.create_text(
            text_x + T.px(2), T.px(self.HEIGHT) // 2 + T.px(14), anchor="w", text=TAGLINE,
            fill=T.TEXT_MUTED, font=(T.BODY, 9),
        )
        self._badge()
        self.bind("<Configure>", self._schedule, add="+")

    def _badge(self) -> None:
        """A quiet 'runs offline' reassurance on the right."""
        self._badge_items = (
            self.create_text(0, 0, anchor="e", text="Private by default",
                             fill=T.TEXT_BODY, font=(T.BODY_MEDIUM, 9)),
            self.create_text(0, 0, anchor="e", text="Nothing is uploaded",
                             fill=T.TEXT_MUTED, font=(T.BODY, 8)),
        )

    def _schedule(self, _event=None) -> None:
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(60, self._render)

    def _render(self) -> None:
        self._resize_job = None
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1 or w == self._width:
            return
        self._width = w
        self._backdrop = ImageTk.PhotoImage(
            ImageOps.fit(self._source, (w, h), Image.LANCZOS, centering=(0.0, 0.5)))
        self.itemconfigure(self._bg_item, image=self._backdrop)
        self.tag_lower(self._bg_item)
        right = w - T.px(26)
        self.coords(self._badge_items[0], right, h // 2 - T.px(9))
        self.coords(self._badge_items[1], right, h // 2 + T.px(10))


# =============================================================================
class FileCard(W.Surface):
    """The pick-an-audio-file zone. The whole card is the target."""

    HEIGHT = 114

    def __init__(self, master, on_pick):
        super().__init__(
            master, on=T.BG, radius=T.px(T.RADIUS), fill=T.SURFACE_1,
            border=T.BORDER_STRONG, dashed=True, height=T.px(self.HEIGHT),
        )
        self._on_pick = on_pick
        self._has_file = False
        self.configure(cursor="hand2", height=T.px(self.HEIGHT))

        self._wave = []
        self._title = self.create_text(0, 0, text="Choose an audio file",
                                       fill=T.TEXT_HEADING, font=(T.DISPLAY_MEDIUM, 13))
        self._subtitle = self.create_text(
            0, 0, text="MP3, WAV, M4A, OGG, FLAC or any video file",
            fill=T.TEXT_MUTED, font=(T.BODY, 9))

        self.bind("<Configure>", lambda _e: self._layout(), add="+")
        self.bind("<Button-1>", lambda _e: self._on_pick(), add="+")
        self.bind("<Enter>", self._enter, add="+")
        self.bind("<Leave>", self._leave, add="+")

    # -- waveform flourish --------------------------------------------------
    def _draw_wave(self, cx: int, cy: int) -> None:
        for item in self._wave:
            self.delete(item)
        self._wave = []
        pattern = [0.30, 0.55, 0.85, 1.0, 0.70, 0.42, 0.66, 1.0, 0.80, 0.48, 0.26]
        gap, unit = T.px(7), T.px(15)
        span = gap * (len(pattern) - 1)
        x = cx - span // 2
        for i, amp in enumerate(pattern):
            colour = T.mix(T.PRIMARY, T.CYAN, i / (len(pattern) - 1))
            half = max(int(unit * amp), T.px(2))
            self._wave.append(self.create_line(
                x, cy - half, x, cy + half, fill=colour,
                width=T.px(3), capstyle="round"))
            x += gap

    def _layout(self) -> None:
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1:
            return
        cx = w // 2
        if self._has_file:
            self.coords(self._title, cx, h // 2 - T.px(6))
            self.coords(self._subtitle, cx, h // 2 + T.px(18))
            for item in self._wave:
                self.delete(item)
            self._wave = []
        else:
            self._draw_wave(cx, h // 2 - T.px(24))
            self.coords(self._title, cx, h // 2 + T.px(10))
            self.coords(self._subtitle, cx, h // 2 + T.px(33))

    # -- state --------------------------------------------------------------
    def show_file(self, path: Path) -> None:
        self._has_file = True
        self.itemconfigure(self._title, text=path.name, font=(T.DISPLAY_MEDIUM, 12))
        self.itemconfigure(
            self._subtitle,
            text=f"{human_size(path.stat().st_size)}  ·  click to choose a different file")
        self.restyle(dashed=False, border=T.PRIMARY, fill=T.SURFACE_2)
        self._layout()

    def reset(self) -> None:
        self._has_file = False
        self.itemconfigure(self._title, text="Choose an audio file",
                           font=(T.DISPLAY_MEDIUM, 13))
        self.itemconfigure(self._subtitle,
                           text="MP3, WAV, M4A, OGG, FLAC or any video file")
        self.restyle(dashed=True, border=T.BORDER_STRONG, fill=T.SURFACE_1)
        self._layout()

    def _enter(self, _e=None) -> None:
        self.restyle(border=T.PRIMARY_GLOW,
                     fill=T.SURFACE_2 if self._has_file else T.SURFACE_1)

    def _leave(self, _e=None) -> None:
        self.restyle(border=T.PRIMARY if self._has_file else T.BORDER_STRONG,
                     fill=T.SURFACE_2 if self._has_file else T.SURFACE_1)


# =============================================================================
class StribeApp(tk.Frame):
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master, bg=T.BG)
        self.grid(row=0, column=0, sticky="nsew")
        master.rowconfigure(0, weight=1)
        master.columnconfigure(0, weight=1)

        self.audio_path: Path | None = None
        self.events: queue.Queue = queue.Queue()
        self.worker: threading.Thread | None = None
        self._models: dict[str, object] = {}
        self._start_time = 0.0
        self._busy = False

        self._build()
        self.after(100, self._drain_events)

    # ---------------------------------------------------------------- layout
    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        Header(self).grid(row=0, column=0, sticky="ew")

        pad = T.px(26)

        self.file_card = FileCard(self, self.browse)
        self.file_card.grid(row=1, column=0, sticky="ew", padx=pad, pady=(T.px(18), 0))

        self._build_options(row=2, pad=pad)
        self._build_action(row=3, pad=pad)
        self._build_transcript(row=4, pad=pad)

        self.toast = W.Toast(self, on=T.BG)

    def _build_options(self, row: int, pad: int) -> None:
        card = W.Card(self, on=T.BG, fill=T.SURFACE_2, padding=18)
        card.grid(row=row, column=0, sticky="ew", padx=pad, pady=(T.px(12), 0))
        # body is place()d, so the frame has no natural height - set it explicitly.
        card.configure(height=T.px(132))
        card.grid_propagate(False)
        body = card.body
        body.columnconfigure(0, weight=1)

        tk.Label(body, text="MODEL", bg=T.SURFACE_2, fg=T.TEXT_MUTED,
                 font=(T.BODY_SEMIBOLD, 8)).grid(row=0, column=0, sticky="w")
        tk.Label(body, text="LANGUAGE", bg=T.SURFACE_2, fg=T.TEXT_MUTED,
                 font=(T.BODY_SEMIBOLD, 8)).grid(row=0, column=1, sticky="w", padx=(T.px(24), 0))

        self.model = W.Segmented(
            body, [name for name, _ in MODELS], on=T.SURFACE_2, value="base",
            command=self._on_model_change, item_width=72, height=32,
        )
        self.model.grid(row=1, column=0, sticky="w", pady=(T.px(8), 0))

        self.language = W.Select(
            body, [name for name, _ in LANGUAGES], on=T.SURFACE_2,
            value="Detect automatically", width=176, height=32,
        )
        self.language.grid(row=1, column=1, sticky="w", padx=(T.px(24), 0), pady=(T.px(8), 0))

        self.model_hint = tk.Label(
            body, text=MODEL_HINTS["base"], bg=T.SURFACE_2, fg=T.TEXT_BODY,
            font=(T.BODY, 9), anchor="w")
        self.model_hint.grid(row=2, column=0, columnspan=2, sticky="w", pady=(T.px(12), 0))

    def _build_action(self, row: int, pad: int) -> None:
        bar = tk.Frame(self, bg=T.BG)
        bar.grid(row=row, column=0, sticky="ew", padx=pad, pady=(T.px(14), 0))
        bar.columnconfigure(1, weight=1)

        self.transcribe_btn = W.Button(
            bar, "Transcribe", self.start_transcribe, on=T.BG, variant="primary",
            width=176, height=46, icon="✦", font=(T.BODY_SEMIBOLD, 11),
        )
        self.transcribe_btn.grid(row=0, column=0, sticky="w")
        self.transcribe_btn.set_enabled(False)

        status = tk.Frame(bar, bg=T.BG)
        status.grid(row=0, column=1, sticky="e")

        self.status = tk.Label(status, text="Pick a file to get started", bg=T.BG,
                               fg=T.TEXT_MUTED, font=(T.BODY, 9), anchor="e")
        self.status.pack(anchor="e")

        self.shimmer = W.ShimmerBar(status, on=T.BG, width=210, height=5)
        self.shimmer.pack(anchor="e", pady=(T.px(8), 0))
        self.shimmer.pack_forget()

    def _build_transcript(self, row: int, pad: int) -> None:
        card = W.Card(self, on=T.BG, fill=T.SURFACE_1, padding=16)
        card.grid(row=row, column=0, sticky="nsew", padx=pad, pady=(T.px(14), T.px(18)))
        body = card.body
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        head = tk.Frame(body, bg=T.SURFACE_1)
        head.grid(row=0, column=0, sticky="ew", pady=(0, T.px(10)))
        head.columnconfigure(1, weight=1)

        tk.Label(head, text="Transcript", bg=T.SURFACE_1, fg=T.TEXT_HEADING,
                 font=(T.DISPLAY_MEDIUM, 11)).grid(row=0, column=0, sticky="w")
        self.count = tk.Label(head, text="", bg=T.SURFACE_1, fg=T.TEXT_MUTED,
                              font=(T.BODY, 9))
        self.count.grid(row=0, column=1, sticky="w", padx=(T.px(12), 0))

        actions = tk.Frame(head, bg=T.SURFACE_1)
        actions.grid(row=0, column=2, sticky="e")
        self.copy_btn = W.Button(actions, "Copy", self.copy_text, on=T.SURFACE_1,
                                 variant="secondary", width=96, height=34,
                                 font=(T.BODY_MEDIUM, 9))
        self.copy_btn.grid(row=0, column=0, padx=(0, T.px(8)))
        self.save_btn = W.Button(actions, "Save .txt", self.save_text, on=T.SURFACE_1,
                                 variant="secondary", width=110, height=34,
                                 font=(T.BODY_MEDIUM, 9))
        self.save_btn.grid(row=0, column=1, padx=(0, T.px(8)))
        self.clear_btn = W.Button(actions, "Clear", self.clear, on=T.SURFACE_1,
                                  variant="ghost", width=76, height=34,
                                  font=(T.BODY_MEDIUM, 9))
        self.clear_btn.grid(row=0, column=2)

        pane = tk.Frame(body, bg=T.BG)
        pane.grid(row=1, column=0, sticky="nsew")
        pane.columnconfigure(0, weight=1)
        pane.rowconfigure(0, weight=1)

        self.text = tk.Text(
            pane, wrap="word", undo=True, relief="flat", bd=0, highlightthickness=0,
            bg=T.BG, fg=T.TEXT_BODY, insertbackground=T.PRIMARY_GLOW,
            selectbackground="#1D4ED8", selectforeground=T.TEXT_HEADING,
            font=(T.BODY, 11), padx=T.px(16), pady=T.px(14),
            spacing1=T.px(2), spacing2=T.px(4), spacing3=T.px(6),
        )
        self.text.grid(row=0, column=0, sticky="nsew")

        self.scroll = W.SlimScrollbar(pane, on=T.BG, width=6)
        self.scroll.grid(row=0, column=1, sticky="ns", padx=(T.px(4), T.px(4)),
                         pady=T.px(6))
        self.scroll.command = self.text.yview
        self.text.configure(yscrollcommand=self.scroll.set)
        self.text.bind("<<Modified>>", self._on_text_modified, add="+")

        self.placeholder = tk.Label(
            pane, bg=T.BG, fg="#4A5B78", font=(T.BODY, 10), justify="center",
            text="Your transcript will appear here.\n"
                 "Pick a file, choose a model, then press Transcribe.")
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")

        self.copy_btn.set_enabled(False)
        self.save_btn.set_enabled(False)

    # --------------------------------------------------------------- actions
    def _on_model_change(self, name: str) -> None:
        self.model_hint.configure(text=MODEL_HINTS[name])

    def browse(self) -> None:
        if self._busy:
            return
        path = filedialog.askopenfilename(title="Select an audio file", filetypes=AUDIO_TYPES)
        if not path:
            return
        self.audio_path = Path(path)
        self.file_card.show_file(self.audio_path)
        self.transcribe_btn.set_enabled(True)
        self.status.configure(text="Ready when you are", fg=T.TEXT_BODY)

    def start_transcribe(self) -> None:
        if not self.audio_path or self._busy:
            return
        if not self.audio_path.exists():
            messagebox.showerror("File missing", f"Can't find:\n{self.audio_path}")
            return

        model_name = self.model.get()
        language = LANGUAGE_CODES[self.language.get()]

        self._set_busy(True)
        self._replace_text("")
        self._start_time = time.time()

        self.worker = threading.Thread(
            target=self._run_transcription,
            args=(self.audio_path, model_name, language),
            daemon=True,
        )
        self.worker.start()

    def _run_transcription(self, path: Path, model_name: str, language: str | None) -> None:
        """Background thread; reports back through self.events."""
        try:
            model = self._models.get(model_name)
            if model is None:
                self.events.put(("status", f"Loading the {model_name} model…"))
                import whisper                       # lazy, so the window opens instantly
                model = whisper.load_model(model_name)
                self._models[model_name] = model

            self.events.put(("status", "Listening to your audio…"))
            result = model.transcribe(str(path), language=language, fp16=False)
            self.events.put(("done", result["text"].strip()))
        except Exception:                            # noqa: BLE001
            self.events.put(("error", traceback.format_exc()))

    def _drain_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "status":
                    self.status.configure(text=payload, fg=T.TEXT_BODY)
                elif kind == "done":
                    self._finish(payload)
                elif kind == "error":
                    self._fail(payload)
        except queue.Empty:
            pass
        self.after(100, self._drain_events)

    def _finish(self, text: str) -> None:
        self._set_busy(False)
        self._replace_text(text)
        elapsed = time.time() - self._start_time
        if text:
            self.status.configure(
                text=f"Done in {self._duration(elapsed)}", fg=T.SUCCESS)
            self.toast.show("Transcript ready")
        else:
            self.status.configure(text="No speech detected in that file", fg=T.TEXT_MUTED)

    def _fail(self, tb: str) -> None:
        self._set_busy(False)
        self.status.configure(text="Transcription failed", fg=T.DANGER)
        last_line = tb.strip().splitlines()[-1]
        messagebox.showerror("Transcription failed", f"{last_line}\n\n{tb[-1500:]}")

    @staticmethod
    def _duration(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.0f}s"
        return f"{int(seconds // 60)}m {int(seconds % 60):02d}s"

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.transcribe_btn.set_enabled(not busy and self.audio_path is not None)
        self.file_card.configure(cursor="arrow" if busy else "hand2")
        if busy:
            self.shimmer.pack(anchor="e", pady=(T.px(8), 0))
            self.shimmer.start()
        else:
            self.shimmer.stop()
            self.shimmer.pack_forget()

    # ------------------------------------------------------------------ text
    def _replace_text(self, value: str) -> None:
        self.text.delete("1.0", "end")
        if value:
            self.text.insert("1.0", value)
        self._refresh_text_state()

    def _on_text_modified(self, _event=None) -> None:
        self.text.edit_modified(False)
        self._refresh_text_state()

    def _refresh_text_state(self) -> None:
        content = self.text.get("1.0", "end-1c").strip()
        if content:
            self.placeholder.place_forget()
            words = len(content.split())
            self.count.configure(text=f"{words:,} words · {len(content):,} characters")
        else:
            self.placeholder.place(relx=0.5, rely=0.5, anchor="center")
            self.count.configure(text="")
        self.copy_btn.set_enabled(bool(content))
        self.save_btn.set_enabled(bool(content))

    def copy_text(self) -> None:
        content = self.text.get("1.0", "end-1c")
        if not content.strip():
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        self.update()                     # survive the app closing
        self.toast.show("Copied to clipboard")

    def save_text(self) -> None:
        content = self.text.get("1.0", "end-1c")
        if not content.strip():
            return
        default = (self.audio_path.stem + ".txt") if self.audio_path else "transcript.txt"
        path = filedialog.asksaveasfilename(
            title="Save transcript", defaultextension=".txt", initialfile=default,
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        Path(path).write_text(content, encoding="utf-8")
        self.toast.show(f"Saved to {Path(path).name}")

    def clear(self) -> None:
        if self._busy:
            return
        self._replace_text("")
        self.audio_path = None
        self.file_card.reset()
        self.transcribe_btn.set_enabled(False)
        self.status.configure(text="Pick a file to get started", fg=T.TEXT_MUTED)


# =============================================================================
def _claim_app_identity() -> None:
    """Tell Windows this process is Stribe, not Python.

    Without an explicit AppUserModelID the taskbar inherits pythonw.exe's
    identity, so the app shows the generic Python icon and groups under it.
    """
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:                                # noqa: BLE001
        pass


def _enable_dpi_awareness() -> None:
    """Render crisply on scaled displays instead of being bitmap-stretched."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:                                # noqa: BLE001
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:                            # noqa: BLE001
            pass


def _dark_titlebar(root: tk.Tk) -> None:
    """Match the Windows title bar to the app instead of a white strip."""
    if sys.platform != "win32":
        return
    try:
        root.update_idletasks()
        hwnd = int(root.wm_frame(), 16)
        for attribute in (20, 19):                   # 20 = Win11/late Win10, 19 = early
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int))
    except Exception:                                # noqa: BLE001
        pass


def _work_area(root: tk.Tk) -> tuple[int, int, int, int]:
    """The desktop minus the taskbar. winfo_screenheight() includes it."""
    if sys.platform == "win32":
        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
        rect = RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
            return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()


def _place_window(root: tk.Tk, *, width: int, height: int) -> None:
    """Open centred inside the work area, frame included."""
    area_x, area_y, area_w, area_h = _work_area(root)

    # Tk geometry sizes the client area; the title bar and borders sit outside it.
    frame_h, frame_w = T.px(40), T.px(16)

    w = min(T.px(width), area_w - frame_w)
    h = min(T.px(height), area_h - frame_h)
    x = area_x + max(0, (area_w - w) // 2)
    y = area_y + max(0, (area_h - h - frame_h) // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")


def main() -> None:
    _claim_app_identity()
    _enable_dpi_awareness()
    T.load_fonts()

    root = tk.Tk()
    root.title(APP_NAME)
    root.configure(bg=T.BG)

    factor = root.winfo_fpixels("1i") / 96.0
    T.set_scale(factor)
    root.tk.call("tk", "scaling", factor * 96.0 / 72.0)
    _place_window(root, width=940, height=780)
    root.minsize(T.px(780), T.px(680))

    T.resolve_fonts(set(tkfont.families(root)))

    icon = T.ASSETS / "stribe.ico"
    if icon.exists():
        try:
            root.iconbitmap(default=str(icon))
        except tk.TclError:
            pass

    StribeApp(root)
    _dark_titlebar(root)
    root.mainloop()


if __name__ == "__main__":
    main()
