"""Custom dark-theme widgets for Stribe.

Tk has no rounded corners, gradients or glows, so every surface here is
rendered with Pillow at 4x and downsampled onto the known parent colour.
That keeps edges antialiased without relying on real window transparency.
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable, Sequence

from PIL import Image, ImageDraw, ImageFilter, ImageTk

import theme as T

_SS = 4  # supersampling factor


# ------------------------------------------------------------------ painting
def _gradient(size: tuple[int, int], stops: Sequence[str], horizontal: bool = True) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)
    span = (w if horizontal else h) or 1
    segments = len(stops) - 1
    for i in range(span):
        t = i / (span - 1) if span > 1 else 0.0
        pos = min(t * segments, segments - 1e-9)
        idx = int(pos)
        colour = T.mix(stops[idx], stops[idx + 1], pos - idx)
        if horizontal:
            draw.line([(i, 0), (i, h)], fill=colour)
        else:
            draw.line([(0, i), (w, i)], fill=colour)
    return img


def _round_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return mask


def paint(
    w: int,
    h: int,
    *,
    on: str,
    radius: int = T.RADIUS,
    fill: str | None = None,
    gradient: Sequence[str] | None = None,
    border: str | None = None,
    border_w: int = 1,
    glow: str | None = None,
    glow_strength: float = 0.55,
    pad: int = 0,
    dashed: bool = False,
) -> ImageTk.PhotoImage:
    """Render one rounded surface, composited onto the solid colour `on`.

    `pad` reserves room around the shape so a glow has somewhere to fall.
    """
    W, H = (w + 2 * pad) * _SS, (h + 2 * pad) * _SS
    r, bw, off = radius * _SS, border_w * _SS, pad * _SS
    box = (off, off, off + w * _SS - 1, off + h * _SS - 1)

    canvas = Image.new("RGB", (W, H), on)

    if glow:
        halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(halo).rounded_rectangle(box, radius=r, fill=glow)
        halo = halo.filter(ImageFilter.GaussianBlur(max(off * 0.55, 6)))
        alpha = halo.split()[-1].point(lambda v: int(v * glow_strength))
        halo.putalpha(alpha)
        canvas = Image.alpha_composite(canvas.convert("RGBA"), halo).convert("RGB")

    shape_mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shape_mask).rounded_rectangle(box, radius=r, fill=255)

    if gradient:
        body = _gradient((w * _SS, h * _SS), gradient)
        layer = Image.new("RGB", (W, H), on)
        layer.paste(body, (off, off))
        canvas = Image.composite(layer, canvas, shape_mask)
    elif fill:
        layer = Image.new("RGB", (W, H), fill)
        canvas = Image.composite(layer, canvas, shape_mask)

    if border:
        draw = ImageDraw.Draw(canvas)
        inset = (box[0] + bw // 2, box[1] + bw // 2, box[2] - bw // 2, box[3] - bw // 2)
        if dashed:
            _dashed_round_rect(draw, inset, r, border, bw)
        else:
            draw.rounded_rectangle(inset, radius=r, outline=border, width=bw)

    return ImageTk.PhotoImage(canvas.resize((W // _SS, H // _SS), Image.LANCZOS))


def _dashed_round_rect(draw: ImageDraw.ImageDraw, box, radius: int, colour: str, width: int) -> None:
    """Dashed outline along the straight runs; solid through the corners."""
    x0, y0, x1, y1 = box
    dash, gap = 14 * _SS, 10 * _SS
    for x in range(x0 + radius, x1 - radius, dash + gap):
        end = min(x + dash, x1 - radius)
        draw.line([(x, y0), (end, y0)], fill=colour, width=width)
        draw.line([(x, y1), (end, y1)], fill=colour, width=width)
    for y in range(y0 + radius, y1 - radius, dash + gap):
        end = min(y + dash, y1 - radius)
        draw.line([(x0, y), (x0, end)], fill=colour, width=width)
        draw.line([(x1, y), (x1, end)], fill=colour, width=width)
    d = radius * 2
    for xy, start in (
        ((x0, y0, x0 + d, y0 + d), 180),
        ((x1 - d, y0, x1, y0 + d), 270),
        ((x1 - d, y1 - d, x1, y1), 0),
        ((x0, y1 - d, x0 + d, y1), 90),
    ):
        draw.arc(xy, start, start + 90, fill=colour, width=width)


# -------------------------------------------------------------------- canvas
class Surface(tk.Canvas):
    """A canvas that repaints a rounded background whenever it is resized."""

    def __init__(self, master, *, on: str, width: int = 0, height: int = 0, **paint_kw):
        # width/height are canvas geometry, never painting options.
        super().__init__(
            master, bg=on, highlightthickness=0, bd=0,
            width=width, height=height, takefocus=0, relief="flat",
        )
        self._on = on
        self._paint_kw = paint_kw
        self._img: ImageTk.PhotoImage | None = None
        self._item = None
        self._size = (0, 0)
        self.bind("<Configure>", self._on_configure, add="+")

    def restyle(self, **paint_kw) -> None:
        self._paint_kw.update(paint_kw)
        self._size = (0, 0)          # force repaint
        self._repaint()

    def _on_configure(self, _event=None) -> None:
        self._repaint()

    def _repaint(self) -> None:
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1 or h <= 1 or (w, h) == self._size:
            return
        self._size = (w, h)
        pad = self._paint_kw.get("pad", 0)
        self._img = paint(w - 2 * pad, h - 2 * pad, on=self._on, **self._paint_kw)
        if self._item is None:
            self._item = self.create_image(0, 0, anchor="nw", image=self._img)
        else:
            self.itemconfigure(self._item, image=self._img)
        self.tag_lower(self._item)


class Card(tk.Frame):
    """A rounded Layer-2 panel with real child widgets inside it."""

    def __init__(
        self,
        master,
        *,
        on: str = T.BG,
        fill: str = T.SURFACE_2,
        border: str | None = T.BORDER,
        radius: int = T.RADIUS,
        padding: int = 16,
        **kw,
    ):
        super().__init__(master, bg=on, **kw)
        padding = T.px(padding)
        self._bg = Surface(self, on=on, fill=fill, border=border, radius=T.px(radius))
        self._bg.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.body = tk.Frame(self, bg=fill)
        self.body.place(x=padding, y=padding, relwidth=1, relheight=1,
                        width=-2 * padding, height=-2 * padding)
        self.fill = fill


# ------------------------------------------------------------------- buttons
class Button(Surface):
    """A canvas-drawn button: gradient primary, glass secondary, or ghost."""

    VARIANTS = {
        "primary": dict(
            gradient=("#2563EB", "#4F46E5"), border=None, fg=T.TEXT_HEADING,
            hover_gradient=("#3B82F6", "#6366F1"), glow=T.PRIMARY,
        ),
        "secondary": dict(
            fill=T.SURFACE_2, border=T.BORDER_STRONG, fg=T.TEXT_BODY,
            hover_fill=T.SURFACE_3, hover_fg=T.TEXT_HEADING,
        ),
        "ghost": dict(
            fill=None, border=None, fg=T.TEXT_MUTED,
            hover_fill=T.SURFACE_1, hover_fg=T.TEXT_BODY,
        ),
    }

    def __init__(
        self,
        master,
        text: str,
        command: Callable[[], None],
        *,
        on: str = T.BG,
        variant: str = "secondary",
        width: int = 150,
        height: int = 44,
        icon: str = "",
        font: tuple | None = None,
        radius: int = T.RADIUS_SM + 2,
    ):
        width, height, radius = T.px(width), T.px(height), T.px(radius)
        self._spec = dict(self.VARIANTS[variant])
        self._variant = variant
        self._on = on
        self._command = command
        self._enabled = True
        self._hover = False
        self._glow_pad = T.px(12) if variant == "primary" else 0

        super().__init__(
            master, on=on, width=width + 2 * self._glow_pad,
            height=height + 2 * self._glow_pad, radius=radius,
            pad=self._glow_pad,
            **self._base_paint(False),
        )
        self.configure(width=width + 2 * self._glow_pad, height=height + 2 * self._glow_pad)

        label = f"{icon}  {text}".strip() if icon else text
        self._text_id = self.create_text(
            (width + 2 * self._glow_pad) / 2, (height + 2 * self._glow_pad) / 2,
            text=label, fill=self._spec["fg"],
            font=font or (T.BODY_SEMIBOLD, 10),
        )
        self.configure(cursor="hand2")
        for seq, handler in (
            ("<Enter>", self._enter), ("<Leave>", self._leave),
            ("<Button-1>", self._press), ("<ButtonRelease-1>", self._release),
        ):
            self.bind(seq, handler, add="+")

    # -- painting -----------------------------------------------------------
    def _base_paint(self, hover: bool) -> dict:
        s = self._spec
        kw: dict = {}
        if s.get("gradient"):
            kw["gradient"] = s["hover_gradient"] if hover else s["gradient"]
            if s.get("glow"):
                kw["glow"] = s["glow"]
                kw["glow_strength"] = 0.75 if hover else 0.35
        else:
            fill = s.get("hover_fill") if hover else s.get("fill")
            kw["fill"] = fill or self._on
        if s.get("border"):
            kw["border"] = s["border"]
        return kw

    def _apply(self, hover: bool) -> None:
        self.restyle(**self._base_paint(hover))
        self.itemconfigure(
            self._text_id,
            fill=(self._spec.get("hover_fg", self._spec["fg"]) if hover else self._spec["fg"]),
        )

    # -- state --------------------------------------------------------------
    def set_enabled(self, enabled: bool) -> None:
        if enabled == self._enabled:
            return
        self._enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        if enabled:
            self._apply(False)
        else:
            self.restyle(
                gradient=None, fill=T.SURFACE_1,
                border=T.BORDER if self._spec.get("border") else None,
                glow=None,
            )
            self.itemconfigure(self._text_id, fill="#48566F")

    # -- events -------------------------------------------------------------
    def _enter(self, _e=None) -> None:
        if self._enabled:
            self._hover = True
            self._apply(True)

    def _leave(self, _e=None) -> None:
        if self._enabled:
            self._hover = False
            self._apply(False)

    def _press(self, _e=None) -> None:
        if self._enabled:
            self.move(self._text_id, 0, 1)

    def _release(self, _e=None) -> None:
        if not self._enabled:
            return
        self.move(self._text_id, 0, -1)
        if self._hover:
            self._command()


# ---------------------------------------------------------------- segmented
class Segmented(tk.Frame):
    """A pill row for picking one of a few options."""

    def __init__(
        self,
        master,
        options: Sequence[str],
        *,
        on: str = T.SURFACE_2,
        value: str | None = None,
        command: Callable[[str], None] | None = None,
        item_width: int = 74,
        height: int = 34,
    ):
        super().__init__(master, bg=on)
        item_width, height = T.px(item_width), T.px(height)
        self._on = on
        self._command = command
        self._value = value or options[0]
        self._cells: dict[str, tk.Canvas] = {}

        for i, option in enumerate(options):
            cell = Surface(self, on=on, radius=T.px(T.RADIUS_SM), width=item_width, height=height)
            cell.configure(width=item_width, height=height, cursor="hand2")
            cell.grid(row=0, column=i, padx=(0, T.px(4)))
            cell._text = cell.create_text(                     # type: ignore[attr-defined]
                item_width / 2, height / 2, text=option,
                font=(T.BODY_MEDIUM, 9), fill=T.TEXT_MUTED,
            )
            cell.bind("<Button-1>", lambda _e, o=option: self.set(o, notify=True), add="+")
            cell.bind("<Enter>", lambda _e, o=option: self._hover(o, True), add="+")
            cell.bind("<Leave>", lambda _e, o=option: self._hover(o, False), add="+")
            self._cells[option] = cell

        self.after(30, lambda: self._render())

    def _hover(self, option: str, entering: bool) -> None:
        if option != self._value:
            self._paint_cell(option, hover=entering)

    def _paint_cell(self, option: str, *, hover: bool = False) -> None:
        cell = self._cells[option]
        selected = option == self._value
        if selected:
            cell.restyle(gradient=("#2563EB", "#4F46E5"), border=None, fill=None)
            cell.itemconfigure(cell._text, fill=T.TEXT_HEADING)   # type: ignore[attr-defined]
        elif hover:
            cell.restyle(gradient=None, fill=T.SURFACE_3, border=None)
            cell.itemconfigure(cell._text, fill=T.TEXT_BODY)      # type: ignore[attr-defined]
        else:
            cell.restyle(gradient=None, fill=T.SURFACE_1, border=None)
            cell.itemconfigure(cell._text, fill=T.TEXT_MUTED)     # type: ignore[attr-defined]

    def _render(self) -> None:
        for option in self._cells:
            self._paint_cell(option)

    def get(self) -> str:
        return self._value

    def set(self, option: str, *, notify: bool = False) -> None:
        if option not in self._cells:
            return
        self._value = option
        self._render()
        if notify and self._command:
            self._command(option)


# ----------------------------------------------------------------- dropdown
class Select(Surface):
    """A dark dropdown - a styled Tk menu, so it themes properly."""

    def __init__(
        self,
        master,
        options: Sequence[str],
        *,
        on: str = T.SURFACE_2,
        value: str | None = None,
        command: Callable[[str], None] | None = None,
        width: int = 168,
        height: int = 34,
    ):
        width, height = T.px(width), T.px(height)
        super().__init__(
            master, on=on, radius=T.px(T.RADIUS_SM), fill=T.SURFACE_1,
            border=T.BORDER_STRONG, width=width, height=height,
        )
        self.configure(width=width, height=height, cursor="hand2")
        self._command = command
        self._value = value or options[0]

        self._label = self.create_text(
            T.px(12), height / 2, anchor="w", text=self._value,
            font=(T.BODY_MEDIUM, 9), fill=T.TEXT_BODY,
        )
        self.create_text(
            width - T.px(14), height / 2, text="▾", font=(T.BODY, 9), fill=T.TEXT_MUTED,
        )

        self._menu = tk.Menu(
            self, tearoff=0, bg=T.SURFACE_2, fg=T.TEXT_BODY,
            activebackground=T.PRIMARY, activeforeground=T.TEXT_HEADING,
            activeborderwidth=0, bd=0, relief="flat",
            font=(T.BODY, 9),
        )
        for option in options:
            self._menu.add_command(label=option, command=lambda o=option: self.set(o, notify=True))

        self.bind("<Button-1>", self._open, add="+")
        self.bind("<Enter>", lambda _e: self.restyle(border=T.PRIMARY), add="+")
        self.bind("<Leave>", lambda _e: self.restyle(border=T.BORDER_STRONG), add="+")

    def _open(self, _e=None) -> None:
        self._menu.tk_popup(self.winfo_rootx(), self.winfo_rooty() + self.winfo_height() + 2)

    def get(self) -> str:
        return self._value

    def set(self, option: str, *, notify: bool = False) -> None:
        self._value = option
        self.itemconfigure(self._label, text=option)
        if notify and self._command:
            self._command(option)


# ----------------------------------------------------------------- progress
class ShimmerBar(tk.Canvas):
    """Indeterminate progress: an accent highlight sweeping a dark track."""

    def __init__(self, master, *, on: str = T.SURFACE_2, width: int = 240, height: int = 6):
        width, height = T.px(width), T.px(height)
        super().__init__(master, bg=on, highlightthickness=0, bd=0,
                         width=width, height=height, takefocus=0)
        self._bar_w, self._bar_h, self._on = width, height, on
        self._pos = 0.0
        self._job: str | None = None
        self._img: ImageTk.PhotoImage | None = None
        self._item = self.create_image(0, 0, anchor="nw")
        self._frames = self._build_frames()
        self._show(0)

    def _build_frames(self, count: int = 40) -> list[ImageTk.PhotoImage]:
        """Pre-render the sweep so animation costs nothing at runtime."""
        frames = []
        w, h = self._bar_w * _SS, self._bar_h * _SS
        radius = h // 2
        mask = _round_mask((w, h), radius)
        band = int(w * 0.42)
        for i in range(count):
            base = Image.new("RGB", (w, h), T.SURFACE_1)
            head = int((i / count) * (w + band) - band)
            strip = _gradient((band, h), (T.SURFACE_1, T.PRIMARY, T.CYAN, T.SURFACE_1))
            base.paste(strip, (head, 0))
            canvas = Image.new("RGB", (w, h), self._on)
            canvas = Image.composite(base, canvas, mask)
            frames.append(ImageTk.PhotoImage(
                canvas.resize((self._bar_w, self._bar_h), Image.LANCZOS)))
        return frames

    def _show(self, index: int) -> None:
        self._img = self._frames[index % len(self._frames)]
        self.itemconfigure(self._item, image=self._img)

    def start(self) -> None:
        if self._job is None:
            self._tick(0)

    def _tick(self, index: int) -> None:
        self._show(index)
        self._job = self.after(28, self._tick, index + 1)

    def stop(self) -> None:
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        self._show(0)


# ---------------------------------------------------------------- scrollbar
class SlimScrollbar(tk.Canvas):
    """A minimal rounded scrollbar that matches the dark surfaces."""

    def __init__(self, master, *, on: str = T.SURFACE_1, width: int = 6):
        width = T.px(width)
        super().__init__(master, bg=on, highlightthickness=0, bd=0,
                         width=width, takefocus=0)
        self._track_w = width
        self._first, self._last = 0.0, 1.0
        self._drag_origin: tuple[float, float] | None = None
        self.command: Callable[..., None] | None = None
        self._thumb = self.create_rectangle(0, 0, 0, 0, fill=T.SURFACE_3, outline="")
        self.bind("<Configure>", lambda _e: self._draw(), add="+")
        self.bind("<Button-1>", self._grab, add="+")
        self.bind("<B1-Motion>", self._drag, add="+")
        self.bind("<Enter>", lambda _e: self.itemconfigure(self._thumb, fill="#41547A"), add="+")
        self.bind("<Leave>", lambda _e: self.itemconfigure(self._thumb, fill=T.SURFACE_3), add="+")

    def set(self, first, last) -> None:
        self._first, self._last = float(first), float(last)
        self._draw()

    def _draw(self) -> None:
        h = self.winfo_height()
        if h <= 1:
            return
        visible = self._last - self._first
        if visible >= 1.0:
            self.itemconfigure(self._thumb, state="hidden")
            return
        self.itemconfigure(self._thumb, state="normal")
        top = self._first * h
        bottom = max(self._last * h, top + T.px(24))
        self.coords(self._thumb, 1, top, self._track_w - 1, bottom)

    def _grab(self, event) -> None:
        self._drag_origin = (event.y, self._first)
        h = self.winfo_height() or 1
        if not (self._first * h <= event.y <= self._last * h):   # jump to click
            target = max(0.0, event.y / h - (self._last - self._first) / 2)
            self._drag_origin = (event.y, target)
            if self.command:
                self.command("moveto", target)

    def _drag(self, event) -> None:
        if self._drag_origin is None or not self.command:
            return
        origin_y, origin_first = self._drag_origin
        h = self.winfo_height() or 1
        self.command("moveto", max(0.0, min(1.0, origin_first + (event.y - origin_y) / h)))


# -------------------------------------------------------------------- toast
class Toast(tk.Frame):
    """A small transient confirmation that fades in over the window."""

    def __init__(self, master, *, on: str = T.BG):
        super().__init__(master, bg=on)
        self._surface = Surface(self, on=on, radius=T.px(T.RADIUS_SM), fill=T.SURFACE_3,
                                border=T.BORDER_STRONG)
        self._surface.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._label = tk.Label(self, text="", bg=T.SURFACE_3, fg=T.TEXT_HEADING,
                               font=(T.BODY_MEDIUM, 9), padx=T.px(14), pady=T.px(8))
        self._label.pack()
        self._job: str | None = None

    def show(self, message: str, *, ms: int = 1900) -> None:
        self._label.configure(text=message)
        self.place(relx=0.5, rely=1.0, anchor="s", y=-T.px(24))
        self.lift()
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(ms, self.hide)

    def hide(self) -> None:
        self._job = None
        self.place_forget()
