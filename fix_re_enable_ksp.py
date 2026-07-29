from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")

p = Path("build.gradle")
content = p.read_text(encoding="utf-8")

old = "// TESTE DIAGNOSTICO: apply plugin: 'com.google.devtools.ksp'\n"
new = "apply plugin: 'com.google.devtools.ksp'\n"

if new in content and old not in content:
    skip("KSP já reativado")
elif old in content:
    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")
    ok("plugin KSP reativado")
