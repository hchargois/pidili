from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
from PIL import Image


type Coords = tuple[int, int]


@dataclass
class Patch:
    pos: Coords
    img: Image.Image


class Differ(ABC):
    @abstractmethod
    def diff(self, before: Image.Image, after: Image.Image) -> list[Patch]:
        raise NotImplementedError


class TileDiffer(Differ):
    def __init__(self, tile_size: tuple[int, int] = (16, 16)):
        self.tile_size = tile_size

    def diff(self, before: Image.Image, after: Image.Image) -> list[Patch]:
        assert before.size == after.size
        assert before.size[0] % self.tile_size[0] == 0
        assert before.size[1] % self.tile_size[1] == 0

        patches: list[Patch] = []

        diff = np.asarray(before) - np.asarray(after)
        tiles = diff.reshape(
            diff.shape[0] // self.tile_size[1],
            self.tile_size[1],
            diff.shape[1] // self.tile_size[0],
            self.tile_size[0] * diff.shape[2],
        ).sum(axis=(1, 3), dtype=np.uint32)

        for y in range(0, before.height, self.tile_size[1]):
            start: int | None = None

            for x in range(0, before.width, self.tile_size[0]):
                tile = tiles[y // self.tile_size[1], x // self.tile_size[0]]
                is_different = tile != 0
                if start is None and is_different:
                    start = x
                elif start is not None and not is_different:
                    patch = after.crop((start, y, x, y + self.tile_size[1]))
                    patches.append(Patch((start, y), patch))
                    start = None

            if start is not None:
                patch = after.crop((start, y, before.width, y + self.tile_size[1]))
                patches.append(Patch((start, y), patch))

        return patches


DefaultDiffer = TileDiffer
