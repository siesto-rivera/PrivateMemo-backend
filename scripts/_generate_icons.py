"""
Generate app icons + splash for class-mobile.
Brand purple (#7c3aed) gradient background + white memo-paper icon.
Run from PrivateMemoBackend venv (Pillow installed).
"""
from PIL import Image, ImageDraw

OUT = "/Users/siesto/MyProject/PrivateMemo/class-mobile/assets/images"

PURPLE_TOP = (139, 92, 246)    # #8b5cf6
PURPLE_BOTTOM = (109, 40, 217)  # #6d28d9
PURPLE_SOLID = (124, 58, 237)   # #7c3aed (brand-500)


def gradient(size, top, bottom, with_alpha=False):
    mode = "RGBA" if with_alpha else "RGB"
    img = Image.new(mode, (size, size))
    d = ImageDraw.Draw(img)
    for y in range(size):
        t = y / max(size - 1, 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        c = (r, g, b, 255) if with_alpha else (r, g, b)
        d.line([(0, y), (size, y)], fill=c)
    return img


def draw_memo(d: ImageDraw.ImageDraw, size, paper=(255, 255, 255), line=(124, 58, 237)):
    """Draw a rounded-rectangle memo with 3 horizontal lines, centered."""
    pad = size * 0.22
    w = size - 2 * pad
    h = w * 1.18
    x = pad
    y = (size - h) / 2

    d.rounded_rectangle([x, y, x + w, y + h], radius=size * 0.06, fill=paper)

    line_h = size * 0.04
    gap = size * 0.08
    pad_x = size * 0.07
    n = 3
    total = n * line_h + (n - 1) * gap
    sy = y + (h - total) / 2
    for i in range(n):
        ly = sy + i * (line_h + gap)
        lw = (w - 2 * pad_x) * (0.6 if i == n - 1 else 1.0)
        d.rounded_rectangle(
            [x + pad_x, ly, x + pad_x + lw, ly + line_h],
            radius=line_h / 2,
            fill=line,
        )


def make_main_icon(size=1024):
    img = gradient(size, PURPLE_TOP, PURPLE_BOTTOM)
    draw_memo(ImageDraw.Draw(img), size)
    return img


def make_foreground(size=1024):
    """Adaptive-icon foreground — transparent BG, memo only, smaller (safe zone)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # Render at 0.7x then center
    inner = Image.new("RGBA", (int(size * 0.7), int(size * 0.7)), (0, 0, 0, 0))
    draw_memo(ImageDraw.Draw(inner), inner.size[0])
    img.paste(inner, ((size - inner.size[0]) // 2, (size - inner.size[1]) // 2), inner)
    return img


def make_background(size=1024):
    img = Image.new("RGB", (size, size), PURPLE_SOLID)
    return img


def make_monochrome(size=1024):
    """Single-color (white) memo shape on transparent — Android themed icons."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inner = Image.new("RGBA", (int(size * 0.7), int(size * 0.7)), (0, 0, 0, 0))
    # White paper, light-gray lines (still single tone — let Android theme color apply)
    draw_memo(ImageDraw.Draw(inner), inner.size[0], paper=(255, 255, 255), line=(180, 180, 180))
    img.paste(inner, ((size - inner.size[0]) // 2, (size - inner.size[1]) // 2), inner)
    return img


def make_splash(size=1024):
    """Splash icon — transparent bg + memo only (so app.json backgroundColor shows around)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inner = Image.new("RGBA", (int(size * 0.55), int(size * 0.55)), (0, 0, 0, 0))
    # White paper with purple lines
    draw_memo(ImageDraw.Draw(inner), inner.size[0])
    img.paste(inner, ((size - inner.size[0]) // 2, (size - inner.size[1]) // 2), inner)
    return img


def make_favicon(size=48):
    img = make_main_icon(256).resize((size, size), Image.LANCZOS)
    return img


def save(img, path, optimize=True):
    if img.mode == "RGB":
        img.save(path, "PNG", optimize=optimize)
    else:
        img.save(path, "PNG", optimize=optimize)
    print(f"  wrote {path}")


def main():
    print("Generating icons...")
    save(make_main_icon(1024), f"{OUT}/icon.png")
    save(make_foreground(1024), f"{OUT}/android-icon-foreground.png")
    save(make_background(1024), f"{OUT}/android-icon-background.png")
    save(make_monochrome(1024), f"{OUT}/android-icon-monochrome.png")
    save(make_splash(1024), f"{OUT}/splash-icon.png")
    save(make_favicon(48), f"{OUT}/favicon.png")
    print("Done.")


if __name__ == "__main__":
    main()
