from PIL import Image, ImageDraw
from pathlib import Path

def ok(msg): print(f"[OK] {msg}")

densities = {"mdpi": 1.0, "hdpi": 1.5, "xhdpi": 2.0, "xxhdpi": 3.0}

def draw_house(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    margin = size * (1 - 66/108) / 2
    inner = size - 2 * margin
    cx = size / 2
    fg_color = (60, 64, 67, 255)
    roof_top = (cx, margin + inner * 0.05)
    roof_left = (margin + inner * 0.08, margin + inner * 0.45)
    roof_right = (margin + inner * 0.92, margin + inner * 0.45)
    d.polygon([roof_top, roof_left, roof_right], fill=fg_color)
    body_left = margin + inner * 0.20
    body_right = margin + inner * 0.80
    body_top = margin + inner * 0.45
    body_bottom = margin + inner * 0.85
    d.rectangle([body_left, body_top, body_right, body_bottom], fill=fg_color)
    door_left = cx - inner * 0.08
    door_right = cx + inner * 0.08
    door_top = margin + inner * 0.62
    d.rectangle([door_left, door_top, door_right, body_bottom], fill=(0, 0, 0, 0))
    return img

for density, factor in densities.items():
    size = round(108 * factor)
    img = draw_house(size)
    out = Path(f"res/mipmap-{density}/ic_launcher_home_foreground.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, format="PNG")
    ok(f"{out} gerado ({size}x{size})")

handle_densities = {"mdpi": 1.0, "hdpi": 1.5, "xhdpi": 2.0, "xxhdpi": 3.0, "xxxhdpi": 4.0}

def draw_handle(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    margin = size * 0.1
    d.ellipse([margin, margin, size - margin, size - margin], fill=(255,255,255,255), outline=(158,158,158,255), width=max(1, round(size*0.04)))
    return img

for density, factor in handle_densities.items():
    size = round(24 * factor)
    img = draw_handle(size)
    out = Path(f"res/drawable-{density}/ic_widget_resize_handle.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, format="PNG")
    ok(f"{out} gerado ({size}x{size})")
