from PIL import Image
from pathlib import Path
import sys

def ok(msg): print(f"[OK] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

CANDIDATES = [
    Path("/sdcard/Download/icone.png"),
    Path("/sdcard/icone.png"),
    Path("/storage/emulated/0/Download/icone.png"),
    Path("/storage/emulated/0/icone.png"),
    Path.home() / "storage" / "shared" / "Download" / "icone.png",
    Path.home() / "storage" / "shared" / "icone.png",
]

SOURCE = None
for c in CANDIDATES:
    if c.exists():
        SOURCE = c
        break

if SOURCE is None:
    fail("não encontrei icone.png em nenhum local esperado:")
    for c in CANDIDATES:
        print(f"  - {c}")
    sys.exit(1)

ok(f"icone.png encontrado em: {SOURCE}")
src = Image.open(SOURCE).convert("RGBA")

densities = {"mdpi": 1.0, "hdpi": 1.5, "xhdpi": 2.0, "xxhdpi": 3.0}
OVERSCAN = 1.15

for density, factor in densities.items():
    canvas_size = round(108 * factor)
    art_size = round(canvas_size * OVERSCAN)
    art = src.resize((art_size, art_size), Image.LANCZOS)
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    offset = (-(art_size - canvas_size) // 2, -(art_size - canvas_size) // 2)
    canvas.paste(art, offset)
    out = Path(f"res/mipmap-{density}/ic_launcher_home_foreground.png")
    canvas.save(out, format="PNG")
    ok(f"{out} gerado ({canvas_size}x{canvas_size})")
