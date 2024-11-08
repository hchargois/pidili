from pidili.widgets import Widget, ProgressBar, Rect, Text, Coords
from pidili.render import DefaultRenderer

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


renderer = DefaultRenderer()

scene = make_scene()

img = renderer.render(scene)

img.show()
