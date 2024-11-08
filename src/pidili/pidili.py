from typing import Callable

from .render import Renderer, DefaultRenderer
from .diff import Differ, DefaultDiffer
from .widgets import Widget, Coords

from PIL import Image

type PaintFunc = Callable[[Image.Image, Coords], None]


class Pidili:
    def __init__(
        self,
        paint_fn: PaintFunc,
        renderer: Renderer = DefaultRenderer(),
        differ: Differ = DefaultDiffer(),
    ):
        self.paint_func = paint_fn
        self.renderer = renderer
        self.differ = differ

        self._prev_render: Image.Image | None = None

    def update(self, scene: Widget):
        render = self.renderer.render(scene)

        if render is self._prev_render:
            # no changes at all, we can avoid doing the diff
            return

        if self._prev_render is None:
            # first render, paint the full screen
            self.paint_func(render, (0, 0))
        else:
            diff = self.differ.diff(self._prev_render, render)
            for patch in diff:
                self.paint_func(patch.img, patch.pos)

        self._prev_render = render

    def reset(self):
        """Resets the internal state, forcing a full paint on the next update"""
        self._prev_render = None
