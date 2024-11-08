from dataclasses import dataclass
from pidili.widgets import Widget, Layout, SizedWidget
from PIL import Image


@dataclass(frozen=True)
class Circle(Widget):
    radius: int
    color: tuple[int, int, int]

    def layout(self) -> Layout:
        return Layout(size=(2 * self.radius, 2 * self.radius))
        # optionally, you could add
        #     offset=(-self.radius, -self.radius)
        # to the Layout to effectively make the center of the circle be the
        # anchor point instead of the top-left corner

    def render(self) -> Image.Image:
        # new_canvas is just a helper method that creates a transparent
        # Pillow image of the size dictated by the layout
        canvas, draw = self.new_canvas()

        # Use Pillow to draw a circle on the canvas
        draw.circle(
            xy=(self.radius, self.radius),
            radius=self.radius,
            fill=self.color,
        )

        # Return your rendered widget!
        return canvas


@dataclass(frozen=True)
class Ellipse(SizedWidget):
    color: tuple[int, int, int]

    def render(self) -> Image.Image:
        canvas, draw = self.new_canvas()

        draw.ellipse(
            xy=((0, 0), self.size),
            fill=self.color,
        )

        return canvas
