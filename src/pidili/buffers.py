from dataclasses import dataclass
from typing import Self, Literal

from PIL import Image, ImageChops

type Coords = tuple[int, int]
type BufMode = Literal["RGBA", "RGB"]
type Color = tuple[int, int, int] | tuple[int, int, int, int]


@dataclass(slots=True)
class Buffer:
    buf: Image.Image
    clip: Image.Image | None

    @classmethod
    def from_image(cls, image: Image.Image) -> Self:
        if image.mode not in ("RGB", "RGBA"):
            raise ValueError(f"Invalid image mode: {image.mode}")
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        return cls(image, None)

    @classmethod
    def new(cls, size: Coords, fill: Color):
        return cls.from_image(Image.new("RGBA", size, fill))

    def paste(self, other: "Buffer", pos: Coords):
        other_buf = other.buf
        if other.clip is not None:
            other_buf = other_buf.copy()
            new_alpha = ImageChops.multiply(other_buf.getchannel("A"), other.clip)
            other_buf.putalpha(new_alpha)

        work_buf = Image.new("RGBA", self.buf.size, (0, 0, 0, 0))
        work_buf.paste(other_buf, pos)

        self.buf = Image.alpha_composite(self.buf, work_buf)

    def show(self):
        self.buf.show()
