# Pidili

**Pi**llow-based **di**splay **li**brary.

Pidili is a library for rendering simple user interfaces.

The _raison d'être_ of this library is to create UIs for "smart screens" such as those supported by the
[turing-smart-screen-python](https://github.com/mathoudebine/turing-smart-screen-python) project.
These screens are quirky little devices that use a slow serial-over-USB interface, so a whole screen refresh takes more than a second.
However, you are not limited to refreshing the whole screen, you can send partial updates.
For UIs where most of the screen is static, refreshing only the parts that actually changed makes the screen seem much faster.
This library makes it easy to create a UI declaratively, render it and send only the differences to the screen.

## Context

The turing-smart-screen-python project already uses the partial refresh property, as widgets paint themselves directly to the screen, so when you refresh a single widget it only repaints the part of the screen it occupies.

This naive "imperative" approach is simple, but it has many problems:

- it works alright for static interfaces where widgets don't move and always repaint exactly over themselves, but if a widget moves (or is removed) you have to remember to "erase" it from its previous position before repainting it to the new position;
- similarly, if a widget changes size (which is very common for text widgets), the new widget may not overwrite the old one fully and you get some leftover text, this is an oft-reported issue that even has [its own FAQ entry](https://github.com/mathoudebine/turing-smart-screen-python/wiki/Troubleshooting#all-platforms-part-of-old-value-still-displayed-after-refresh-ghosting);
- it is not as efficient as it can be: for widgets that only change a little bit, for example for a progress bar that changes value from 49% to 51%, you have to repaint the whole bar, even if only a few pixels around the middle actually need to be repainted;
- the lack of buffering means you have to paint the screen in layers, e.g. a background image, then the widgets over it, and it's hard to have more layers than that as widgets may corrupt each other if they overlap;
- if you don't want to repaint all the widgets on each frame, you have to manually keep track of which widgets have changed or not;
- to paint a partially transparent widget over a background, you have to pass that background image to the widget being painted so it can first paste itself on top of it then paint itself to the screen.

All of this is tedious, error-prone and slow.

## Goals

Main goals:

- Declarative: describe your UI as a widget tree, the library takes care of rendering, diffing and creating patches to send to the screen
- Extensible: easy to create new widgets
- Simple: to understand, to use, to hack
- Portable: it only depends on Pillow and numpy, which are themselves supported everywhere. No GPU needed.

Non-goals:

- Compatibility with older Python versions: it uses multiple modern Python constructs and requires Python 3.12 or newer;
- Speed: while it's reasonably well optimized since it uses PIL and numpy for image processing, and it tries to minimize re-renderings of widgets, it's still CPU rendering and thus much slower than what a GPU would do; but since the screens have low resolutions it's mostly fine, the USB-serial interface will most likely be the limiting factor rather than the render speed.

## Usage

### Creating a scene and rendering a single frame

A scene is simply a tree of widgets. You start with a root widget and add children to it.
Then, you pass it to the renderer and you get back a Pillow image.

```python
from pidili.widgets import Widget, ProgressBar, Rect, Text, Coords

font = "DejaVuSans.ttf"

def make_scene() -> Widget:
    # You need a root widget, probably a Rect or an Img; this dictates the
    # size of the scene
    scene = Rect((480, 320), fill=(255, 255, 255))

    # Then you add child widgets by calling add(position, widget)
    scene.add((30, 30), Rect((100, 100), fill=(255, 0, 0)))
    scene.add(
        (30, 130), Text("Hello world!", color=(0, 0, 255), font=font, font_size=64)
    )

    # Any widget can itself have children; in that case the position of the child
    # is relative to its parent's (top-left) origin
    green_with_blue_inside = Rect((100, 100), fill=(0, 255, 0))
    green_with_blue_inside.add((20, 20), Rect((60, 60), fill=(0, 0, 255)))
    scene.add((200, 30), green_with_blue_inside)

    # You can use that property to create reusable, composed widgets with a
    # simple function that returns a widget tree
    scene.add((30, 220), my_labeled_progress_bar((420, 30), 40))
    scene.add((30, 260), my_labeled_progress_bar((200, 30), 10))
    scene.add((250, 260), my_labeled_progress_bar((200, 30), 90))

    return scene


def my_labeled_progress_bar(size: Coords, progress: int) -> Widget:
    # positioning the text at the center with the anchor "mm" will make sure
    # the text is perfectly centered in the progress bar
    center = (size[0] // 2, size[1] // 2)

    return ProgressBar(size, progress, bar=(60, 160, 60), border_width=2).add(
        center,
        Text(
            f"{progress} %",
            color=(0, 0, 0),
            font=font,
            font_size=20,
            anchor="mm",
        ),
    )
```

To render the scene, you simply pass it to the renderer which will give you
back a Pillow image.

```python
from pidili.render import DefaultRenderer

renderer = DefaultRenderer()
scene = make_scene()
img = renderer.render(scene)
img.show()
```

![the render of the scene described above](demo.png)

### Updating the scene

OK, so in the above section you've learned how to create and render a single scene, i.e. a single frame of your UI.
How do you render the next frame and update the display?

The idea is to create a whole new scene from scratch on every frame.
Creating a scene, i.e. a tree of widgets, is very cheap since widgets are just containers with a few properties.

After creating the new scene, you pass it to the renderer, which as before will give you back a rendered image.
The renderer is smart enough to only re-render the widgets that have been added or have changed in the scene.

To find the (bitmap) differences between the previous render and the new one, you then use a `Differ`.
The Differ takes the previous and new renders, and outputs a list of patches.
You can finally paint these patches on the screen.

To simplify this process, instead of using a Renderer and a Differ directly, you can use a Pidili instead, which is just a helper that renders, diffs and calls a callback for each patch that needs to be painted.

Supposing you have a `paint_cb(img: Image.Image, position: Coords)` callback, your rendering loop may look something like this:

```python
from pidili import Pidili

# create the Pidili once, with your paint callback
pdl = Pidili(paint_cb)

# whatever state your application needs, e.g. progress bar values
state = MyAppState()

while True:
    # update your app state with your business logic
    state.update()

    # create a new scene from scratch based on the current state
    scene = make_scene(state)

    # that single call to pdl.update will:
    # - render the new scene
    # - diff it with the previous one
    # - paint the patches to the screen using your paint callback
    pdl.update(scene)
```

### Creating new widget classes

A widget is a frozen [dataclass](https://docs.python.org/3/library/dataclasses.html) that inherits from `widgets.Widget` and implements two methods:

- `layout(self) -> Layout`: returns the layout of the widget, i.e. most importantly its size, and optionally an offset from its "anchor" point
- `render(self) -> Image.Image`: returns the rendering of the widget, as a Pillow Image

Using frozen dataclasses makes it easy for Pidili to compare the old and new scenes and only re-render the widgets that have changed, since frozen dataclasses automatically implement an equality function.

For example, this would be a simple Circle widget:

```python
from dataclasses import dataclass
from pidili.widgets import Widget, Layout
from PIL import Image, ImageDraw


@dataclass(frozen=True)
class Circle(Widget):
    radius: int
    color: tuple[int, int, int]

    def layout(self) -> Layout:
        return Layout(size=(2 * self.radius, 2 * self.radius))

    def render(self) -> Image.Image:
        # new_canvas is just a helper method that creates a transparent
        # Pillow image of the size dictated by the layout, and a Pillow
        # ImageDraw object that can be used to draw on the canvas
        canvas, draw = self.new_canvas()

        # Use Pillow's ImageDraw to draw a circle on the canvas
        draw.circle(
            xy=(self.radius, self.radius),
            radius=self.radius,
            fill=self.color,
        )

        # Return your rendered widget!
        return canvas

# Use it like this:
red_circle = Circle(10, (255, 0, 0))
```

Optionally, you could add `offset=(-self.radius, -self.radius)` to the Layout to effectively make the anchor point be the center of the circle instead of the default, the top-left corner.

More often than not, widgets have an explicit size (width, height).
In that case, instead of using `Widget` as the base class, you can use `SizedWidget` instead, which adds a `size` field to the dataclass.
An Ellipse widget that fits a bounding rectangle could be as simple as:

```python
@dataclass(frozen=True)
class Ellipse(SizedWidget):
    # SizedWidget adds a "size" field as the first field
    color: tuple[int, int, int]

    # SizedWidget implements layout(), no need to implement it yourself

    def render(self) -> Image.Image:
        canvas, draw = self.new_canvas()

        draw.ellipse(
            xy=((0, 0), self.size),
            fill=self.color,
        )

        return canvas

# Use it like this:
blue_ellipse = Ellipse((10, 20), (0, 0, 255))
```

When creating widgets, remember that it will be created, and its `layout()` method will be called on every frame to create the scene, therefore this must be cheap.

The `render()` method can be a bit more expensive since it will not be called on every frame if the widget hasn't changed.

# See also

- The original project: [Turing Smart Screen Python](https://github.com/mathoudebine/turing-smart-screen-python)
- My fork of the driver code from the original project: [smartscreen-driver](https://github.com/hchargois/smartscreen-driver) (also available on PyPI)
