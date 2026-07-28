from pathlib import Path
import re

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

candidates = list(Path(".").rglob("Flags.java"))
target = None
for c in candidates:
    content = c.read_text(encoding="utf-8", errors="ignore")
    if "enableSupportForArchiving" in content:
        target = c
        break

if target is None:
    fail("nenhum Flags.java contém 'enableSupportForArchiving'")
else:
    content = target.read_text(encoding="utf-8")
    pattern = re.compile(
        r'(public\s+static\s+boolean\s+enableSupportForArchiving\s*\(\s*\)\s*\{\s*return\s+)(false|true)(\s*;\s*\})'
    )
    m = pattern.search(content)
    if not m:
        fail(f"não encontrei o padrão do método em {target}")
    elif m.group(2) == "false":
        skip("enableSupportForArchiving() já está false")
    else:
        new_content = content[:m.start()] + m.group(1) + "false" + m.group(3) + content[m.end():]
        target.write_text(new_content, encoding="utf-8")
        ok(f"enableSupportForArchiving() revertido para false em {target}")

p = Path("src/com/android/launcher3/model/LoaderTask.java")
if not p.exists():
    fail(f"não encontrei {p}")
    raise SystemExit(1)

content = p.read_text(encoding="utf-8")

old = "                        mInstallingPkgsCached,\n"
new = "                        mInstallingPkgsCached != null ? mInstallingPkgsCached : new HashMap<>(),\n"

if "mInstallingPkgsCached != null ? mInstallingPkgsCached : new HashMap<>()" in content:
    skip("guarda de nulidade já aplicada em LoaderTask.java")
elif old in content:
    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")
    ok("LoaderTask.java: passagem de mInstallingPkgsCached agora usa HashMap vazio como fallback quando null")
else:
    fail("não achei a linha exata 'mInstallingPkgsCached,' com essa indentação — confere manualmente")

print("\nScript concluído.")
