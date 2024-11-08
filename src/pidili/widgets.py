from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Self, NamedTuple, Literal
import math
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from .utils import clamp, Box
from .colors import Color, WHITE, BLACK, TRANSPARENT


# (x, y) or (with, height) tuples
type Coords = tuple[int, int]


@dataclass(slots=True)
class Layout:
    size: Coords = (0, 0)
    offset: Coords = (0, 0)


@dataclass(frozen=True)
class Widget(ABC):
    _children: list["PositionedWidget"] = field(
        init=False, default_factory=list, compare=False, repr=False
    )
    _layout: Box[Layout] = field(
        init=False, default_factory=Box[Layout], compare=False, repr=False
    )

    @abstractmethod
    def layout(self) -> Layout:
        raise NotImplementedError

    @abstractmethod
    def render(self) -> Image.Image:
        raise NotImplementedError

    def get_layout(self) -> Layout:
        if self._layout.value is not None:
            return self._layout.value
        layout = self.layout()
        self._layout.value = layout
        return layout

    def add(self, pos: Coords, child: "Widget") -> "Self":
        child_layout = child.get_layout()
        offseted_pos = (
            pos[0] + child_layout.offset[0],
            pos[1] + child_layout.offset[1],
        )
        self._children.append(PositionedWidget(offseted_pos, child))
        return self

    def new_canvas(
        self, fill: Color = TRANSPARENT
    ) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        layout = self.get_layout()
        canvas = Image.new("RGBA", layout.size, fill)
        return canvas, ImageDraw.Draw(canvas)

    @property
    def width(self) -> int:
        return self.get_layout().size[0]

    @property
    def height(self) -> int:
        return self.get_layout().size[1]


type Anchor = Literal[
    "lt",
    "lm",
    "lb",
    "mt",
    "mm",
    "mb",
    "rt",
    "rm",
    "rb",
]


@dataclass(frozen=True)
class SizedWidget(Widget):
    size: Coords
    anchor: Anchor = field(kw_only=True, default="lt")

    def layout(self) -> Layout:
        if self.anchor == "lt":
            return Layout(size=self.size)

        off_x, off_y = 0, 0
        if self.anchor[0] == "r":
            off_x = -self.size[0]
        elif self.anchor[0] == "m":
            off_x = -self.size[0] // 2

        if self.anchor[1] == "b":
            off_y = -self.size[1]
        elif self.anchor[1] == "m":
            off_y = -self.size[1] // 2

        return Layout(size=self.size, offset=(off_x, off_y))


class PositionedWidget(NamedTuple):
    pos: Coords
    widget: Widget


@dataclass(frozen=True)
class Rect(SizedWidget):
    fill: Color = TRANSPARENT
    stroke: Color | None = None
    stroke_width: int = 1

    def render(self) -> Image.Image:
        canvas, draw = self.new_canvas(self.fill)

        if self.stroke is not None:
            draw.rectangle(
                (0, 0, self.size[0] - 1, self.size[1] - 1),
                outline=self.stroke,
                width=self.stroke_width,
            )

        return canvas


@dataclass(frozen=True)
class ProgressBar(SizedWidget):
    value: int | float  # value between 0 and 100
    bar: Color = WHITE
    border: Color = BLACK
    fill: Color = TRANSPARENT
    border_width: int = 0

    def render(self) -> Image.Image:
        val = clamp(self.value, 0, 100)
        canvas, draw = self.new_canvas()

        draw.rectangle(
            (0, 0, self.size[0] - 1, self.size[1] - 1),
            fill=self.fill,
            outline=self.border,
            width=self.border_width,
        )

        bar_width = int((self.size[0] - 2 * self.border_width) * val / 100)
        if bar_width > 0:
            draw.rectangle(
                (
                    self.border_width,
                    self.border_width,
                    self.border_width + bar_width - 1,
                    self.size[1] - self.border_width - 1,
                ),
                fill=self.bar,
            )

        return canvas


@dataclass(frozen=True)
class Img(SizedWidget):
    """
    Widget that displays an image. Since Pillow Images do not support comparison,
    a key is used to determine if the image has changed. You should use the
    same key every time when the image stays the same, but use a different key
    if the image changes. The file path or URL is probably a good choice."""

    img: Image.Image = field(compare=False)
    key: str

    def render(self) -> Image.Image:
        img = self.img

        if img.mode != "RGBA":
            img = self.img.convert("RGBA")

        if img.size == self.size:
            return img

        return img.resize(self.size)


class _FontCache:
    def __init__(self):
        self._cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}

    def get(self, name: str, size: int) -> ImageFont.FreeTypeFont:
        key = (name, size)
        if key not in self._cache:
            self._cache[key] = ImageFont.truetype(name, size)
        return self._cache[key]


_font_cache = _FontCache()

# only allow anchors that are supported for multi-line text, i.e. not "top" and "bottom" vertical anchors
type TextAnchor = Literal[
    "la",
    "lm",
    "ls",
    "ld",
    "ma",
    "mm",
    "ms",
    "md",
    "ra",
    "rm",
    "rs",
    "rd",
    "sa",
    "sm",
    "ss",
    "sd",
]


@dataclass(frozen=True)
class Text(Widget):
    text: str
    color: Color
    font: str
    font_size: int = 12
    max_width: int | None = None
    anchor: TextAnchor = "la"
    align: str = "left"

    # use a box to cache the (possibly wrapped) text between layout and render
    _text: Box[str] = field(
        init=False, default_factory=Box[str], compare=False, repr=False
    )

    def layout(self) -> Layout:
        text, layout = _text_layout(
            self.text, self.font, self.font_size, self.max_width, self.anchor
        )
        self._text.value = text
        return layout

    def render(self) -> Image.Image:
        canvas, draw = self.new_canvas()
        offset = self.get_layout().offset

        font = _font_cache.get(self.font, self.font_size)

        anchor_pos = (-offset[0], -offset[1])
        draw.text(
            anchor_pos,
            self._text.get(),
            self.color,
            font=font,
            anchor=self.anchor,
            align=self.align,
        )

        return canvas


@lru_cache()
def _text_layout(
    text: str, font: str, font_size: int, max_width: int | None, anchor: str
) -> tuple[str, Layout]:
    f = _font_cache.get(font, font_size)

    if max_width is not None:
        text = _wrap_text(text, f, max_width)

    bbox = _draw.multiline_textbbox((0, 0), text, font=f, anchor=anchor)
    width = _round_away(bbox[2] - bbox[0])
    height = _round_away(bbox[3] - bbox[1])

    left = _round_away(bbox[0])
    top = _round_away(bbox[1])

    return text, Layout(size=(width, height), offset=(left, top))


def _round_away(x: float) -> int:
    if x < 0:
        return math.floor(x)
    return math.ceil(x)


# multiline_textbbox is defined on ImageDraw even though it doesn't actually
# draw anything. To avoid having to create new Image and ImageDraw objects
# every time we need to compute bboxes, we reuse the same one.
_draw = ImageDraw.Draw(Image.new("RGBA", (0, 0), (0, 0, 0)))


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, line_length: int) -> str:
    lines = []
    current_line = ""

    def split_long_word(word: str) -> list:
        """Splits a word into chunks that fit within line_length, ensuring at least one character per chunk."""
        chunks = []
        while word:
            for i in range(1, len(word) + 1):
                if font.getlength(word[:i]) > line_length:
                    if (
                        i == 1
                    ):  # If even one character is too big, force single-character chunks
                        chunks.append(word[:1])
                        word = word[1:]
                    else:
                        chunks.append(word[: i - 1])
                        word = word[i - 1 :]
                    break
            else:
                chunks.append(word)
                break
        return chunks

    for word in text.split():
        new_line = f"{current_line} {word}".strip() if current_line else word

        if font.getlength(new_line) <= line_length:
            current_line = new_line
        else:
            if current_line:
                lines.append(current_line)
            if font.getlength(word) > line_length:
                word_chunks = split_long_word(word)
                lines.extend(word_chunks[:-1])
                current_line = word_chunks[-1]
            else:
                current_line = word

    if current_line:
        lines.append(current_line)

    return "\n".join(lines)
