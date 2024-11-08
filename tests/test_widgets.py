from PIL import ImageFont

from pidili.widgets import _wrap_text

font = ImageFont.truetype("DejaVuSans.ttf", 24)


def test_wrap_text():
    assert _wrap_text("hello world", font, 200) == "hello world"
    assert _wrap_text("hello world", font, 100) == "hello\nworld"
    assert _wrap_text("hello world", font, 40) == "hel\nlo\nwo\nrld"
    assert _wrap_text("helloworld", font, 50) == "hell\nowo\nrld"

    assert _wrap_text("", font, 200) == ""
    assert _wrap_text("hello world", font, 1) == "h\ne\nl\nl\no\nw\no\nr\nl\nd"
