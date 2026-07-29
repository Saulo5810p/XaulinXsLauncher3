from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

p = Path("build.gradle")
content = p.read_text(encoding="utf-8")

old = "    implementation 'androidx.compose.material3:material3'\n"
new = "    implementation 'androidx.compose.material3:material3:1.5.0-alpha24'\n"

if new in content:
    skip("já presente")
elif old in content:
    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")
    ok("material3 sobrescrito para 1.5.0-alpha24")
else:
    fail("não achei a linha material3 no build.gradle")
