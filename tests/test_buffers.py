import os

from PIL import Image, ImageChops

from pidili.buffers import Buffer


def open_test_image(name: str) -> Image.Image:
    module_dir = os.path.dirname(__file__)
    path = os.path.join(module_dir, "data", name)
    return Image.open(path)


def assert_image_equals(image1: Image.Image, image2: Image.Image):
    assert image1.size == image2.size
    # compare alphas only if the 2 images are RGBA
    if not (image1.mode == image2.mode == "RGBA"):
        image1 = image1.convert("RGB")
        image2 = image2.convert("RGB")

    diff = ImageChops.difference(image1, image2)
    assert diff.getbbox(alpha_only=False) is None


def buffers_1() -> Buffer:
    background = Buffer.new((200, 200), (128, 128, 128))

    red = Buffer.new((100, 100), (255, 0, 0))

    blue_transparent = Buffer.new((100, 100), (0, 0, 255, 128))

    background.paste(red, (0, 0))
    background.paste(blue_transparent, (100, 100))

    red_transparent = Buffer.new((100, 100), (255, 0, 0, 128))
    green = Buffer.new((50, 50), (0, 255, 0))
    red_transparent.paste(green, (25, 25))

    background.paste(red_transparent, (50, 50))
    return background


def test_buffers_1():
    result = buffers_1()

    assert_image_equals(result.buf, open_test_image("buffers_1.png"))


def test_buffers_1_bench(benchmark):
    benchmark(test_buffers_1)
