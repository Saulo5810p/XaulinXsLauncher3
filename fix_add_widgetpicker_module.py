from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

p = Path("build.gradle")
content = p.read_text(encoding="utf-8")

old = "                'deferred-appfunctions-widgetpicker',\n"
new = "                'deferred-appfunctions-widgetpicker',\n                'modules/widgetpicker/src',\n"

if "'modules/widgetpicker/src'" in content:
    skip("modules/widgetpicker/src já está incluído")
elif old in content:
    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")
    ok("modules/widgetpicker/src adicionado (motor Dagger/Compose do widget picker)")
else:
    fail("não achei o ponto de ancoragem no build.gradle")
