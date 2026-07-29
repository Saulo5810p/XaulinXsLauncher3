from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

p = Path("build.gradle")
content = p.read_text(encoding="utf-8")

old = "                // 'modules/widgetpicker/res',\n"
new = "                'modules/widgetpicker/res',\n"

if new in content:
    skip("modules/widgetpicker/res já ativo")
elif old in content:
    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")
    ok("modules/widgetpicker/res reativado")
else:
    fail("não achei a linha comentada de modules/widgetpicker/res")
