from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from collections.abc import Callable
import logging

from PIL import Image

from .utils import timed
from .buffers import Buffer
from .widgets import Widget, Coords, PositionedWidget


logger = logging.getLogger(__name__)


class Renderer(ABC):
    @abstractmethod
    def render(self, scene: Widget) -> Image.Image:
        raise NotImplementedError


class NaiveRenderer(Renderer):
    """A basic renderer that renders and pastes all widgets from scratch on
    every frame; this is not efficient but should be simple to understand, and
    should be the standard reference upon which other renderers should be
    judged: they should produce the same outputs, but faster.
    """

    def _render_rec(self, widget: Widget) -> Buffer:
        buf = Buffer.from_image(widget.render())
        for pos, child in widget._children:
            child_buf = self._render_rec(child)
            buf.paste(child_buf, pos)
        return buf

    def render(self, scene: Widget) -> Image.Image:
        return self._render_rec(scene).buf


@dataclass(slots=True)
class Node:
    pos: Coords
    widget: Widget
    render: Image.Image | None = None
    buffer: Buffer | None = None
    children: list["Node"] = field(init=False, default_factory=list)

    def walk(self, func: Callable[["Node"], None]):
        func(self)
        for child in self.children:
            child.walk(func)


def _node_tree(pw: Node, indent: int = 0) -> str:
    attrs = [".", "."]
    if pw.render is not None:
        attrs[0] = "R"
    if pw.buffer is not None:
        attrs[1] = "B"
    attrs = "".join(attrs)
    return f"{'    ' * indent}{attrs} {pw.widget} at {pw.pos}\n" + "".join(
        _node_tree(child, indent + 1) for child in pw.children
    )


class NodeTreeRenderer(Renderer):
    """A renderer that builds a tree of nodes to try matching one scene to the
    next and only render and paste the nodes that have changed."""

    def __init__(self):
        self.old: Node | None = None

    def _copy_renders(self, old: Node, new: Node):
        # copy the renders from widgets in the old scene to identical widgets
        # in the new scene, regardless of whether the widgets are in the same
        # position in both scenes or not. Widgets may have been moved around, it
        # doesn't matter, we can still keep the renders as renders only depend
        # on the widget itself, not the position in the scene
        renders: dict[Widget, Image.Image] = {}

        def retrieve(n: Node):
            assert n.render is not None
            renders[n.widget] = n.render

        old.walk(retrieve)

        def put(n: Node):
            n.render = renders.get(n.widget)

        new.walk(put)

    def _render_widgets(self, node: Node):
        # if the same widget is present multiple times in the scene, this cache
        # allows rendering it only the first time it's encountered
        cache: dict[Widget, Image.Image] = {}

        def render(n: Node):
            if n.render is None:
                if n.widget in cache:
                    n.render = cache[n.widget]
                    return
                logger.debug(f"rendering {n.widget}")
                n.render = n.widget.render()
                cache[n.widget] = n.render

        node.walk(render)

    def _copy_buffers(self, old: Node, new: Node) -> bool:
        identical_children: bool = True
        if len(old.widget._children) != len(new.widget._children):
            identical_children = False

        # even if the count of children is not the same, try to match up as many
        # identical children as possible, it may just be that a child widget was
        # added or removed at the end of the list
        # TODO maybe we should instead try to match up children based on "key"
        # (pos, widget); and if there are still some children that don't match,
        # try to match them with (widget) key alone, maybe they're the same
        # widget (and children) just moved around on the scene
        for old_child, new_child in zip(old.children, new.children):
            if old_child.widget != new_child.widget:
                identical_children = False
                continue
            identical_children = identical_children and old_child.pos == new_child.pos
            identical_children = (
                self._copy_buffers(old_child, new_child) and identical_children
            )

        if identical_children:
            new.buffer = old.buffer

        return identical_children

    def _paste(self, node: Node):
        if node.buffer is not None:
            return

        assert node.render is not None
        node.buffer = Buffer.from_image(node.render)

        for child in node.children:
            self._paste(child)
            assert child.buffer is not None
            node.buffer.paste(child.buffer, child.pos)

    def _create_node_tree(self, pw: PositionedWidget) -> Node:
        root = Node(pw.pos, pw.widget)
        for child in pw.widget._children:
            root.children.append(self._create_node_tree(child))
        return root

    def render(self, scene: Widget) -> Image.Image:
        with timed(logger.debug, "create node tree"):
            new = self._create_node_tree(PositionedWidget((0, 0), scene))

        if self.old is not None:
            with timed(logger.debug, "copy renders phase"):
                self._copy_renders(self.old, new)

            with timed(logger.debug, "copy buffers phase"):
                self._copy_buffers(self.old, new)

        logger.debug("\n" + _node_tree(new))

        with timed(logger.debug, "render phase"):
            self._render_widgets(new)

        with timed(logger.debug, "paste phase"):
            self._paste(new)

        self.old = new

        assert new.buffer is not None
        return new.buffer.buf


DefaultRenderer = NodeTreeRenderer
