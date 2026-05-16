"""Generate PNG icons for the PWA without external dependencies."""
import struct
import zlib
import math


def create_png(size: int, path: str) -> None:
    def pack_chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)

    def make_pixel(r: int, g: int, b: int, a: int = 255) -> bytes:
        return bytes([r, g, b, a])

    # Background gradient: #7C3AED → #5B21B6
    def bg_color(x: int, y: int) -> tuple:
        t = y / size
        r = int(0x7C + (0x5B - 0x7C) * t)
        g = int(0x3A + (0x21 - 0x3A) * t)
        b = int(0xED + (0xB6 - 0xED) * t)
        return r, g, b

    # Draw a scissors-like "✂" shape using pixel art
    cx, cy = size // 2, size // 2
    radius = size * 0.35

    pixels = []
    for y in range(size):
        row = [0]  # filter byte
        for x in range(size):
            dx = x - cx
            dy = y - cy

            # Rounded square background (full canvas for maskable)
            br, bg, bb = bg_color(x, y)

            # White letter "T" in the center
            lw = size * 0.05          # line width
            tw = size * 0.5           # top bar width
            th = size * 0.08          # bar height
            stem_w = size * 0.12      # stem width
            top_y = cy - size * 0.15
            bot_y = cy + size * 0.25

            in_top = (abs(dy - (top_y - cy)) < th and abs(dx) < tw / 2)
            in_stem = (abs(dx) < stem_w / 2 and top_y - cy <= dy <= bot_y - cy)

            if in_top or in_stem:
                row += list(make_pixel(255, 255, 255, 230))
            else:
                row += list(make_pixel(br, bg, bb, 255))

        pixels.append(bytes(row))

    raw = b''.join(pixels)
    compressed = zlib.compress(raw)

    ihdr_data = struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)
    png = (
        b'\x89PNG\r\n\x1a\n'
        + pack_chunk(b'IHDR', ihdr_data)
        + pack_chunk(b'IDAT', compressed)
        + pack_chunk(b'IEND', b'')
    )

    with open(path, 'wb') as f:
        f.write(png)
    print(f"Created {path} ({size}x{size})")


if __name__ == '__main__':
    import os
    base = os.path.dirname(__file__)
    create_png(192, os.path.join(base, 'icon-192.png'))
    create_png(512, os.path.join(base, 'icon-512.png'))
