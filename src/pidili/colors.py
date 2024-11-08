from PIL import ImageColor

type Color = tuple[int, int, int] | tuple[int, int, int, int]

type NamedColor = Color | str

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# fully transparent fuchsia (bright pink), which makes it more obvious than
# transparent black if we somehow draw it on an RGB image instead of RGBA
TRANSPARENT = (255, 0, 255, 0)


def parse_color(color: NamedColor) -> Color:
    if isinstance(color, str):
        return ImageColor.getrgb(color)
    if isinstance(color, tuple):
        if len(color) == 3:
            return color
        if len(color) == 4:
            # simplify an RGBA color with full opacity to an RGB color
            if color[3] == 255:
                return color[:3]
            return color
    raise ValueError(f"Invalid color: {color}")


def is_opaque(color: Color) -> bool:
    return len(color) == 3 or color[3] == 255
