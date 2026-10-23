import struct
from types import SimpleNamespace
import unittest

from dot_palette import DotPalette


class DotOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.platform = bytearray(96)
        self.image = bytearray(96)
        struct.pack_into('<i', self.image, 0, 1)
        self.dot = dict(name='test dot', node='10000', object='20000', data='30000',
                        header=bytes(120).hex(), images=[dict(platform='40000', image_data='50000',
                        platform_header=self.platform.hex(), image_header=self.image.hex())])
        self.memory = {0x10020: struct.pack('<Q', 0x20000),
                       0x20008: struct.pack('<Q', 0x30000), 0x30000: bytes(120),
                       0x40000: self.platform, 0x50000: self.image}
        self.palette = DotPalette.__new__(DotPalette)
        self.palette.s = SimpleNamespace(read=lambda address, count: bytes(self.memory[address][:count]))

    def test_adjacent_allocation_changes_do_not_invalidate_the_80_byte_pixmap(self):
        self.platform[95] = 1
        self.palette.ownership(self.dot)

    def test_changed_image_pointer_is_still_rejected(self):
        self.platform[72] = 1
        with self.assertRaisesRegex(RuntimeError, 'Dot image changed'):
            self.palette.ownership(self.dot)

    def test_changed_dimensions_are_still_rejected(self):
        self.platform[8] = 1
        with self.assertRaisesRegex(RuntimeError, 'Dot image changed'):
            self.palette.ownership(self.dot)

    def test_image_reference_count_can_change_during_painting(self):
        struct.pack_into('<i', self.image, 0, 2)
        self.palette.ownership(self.dot)


if __name__ == '__main__':
    unittest.main()
