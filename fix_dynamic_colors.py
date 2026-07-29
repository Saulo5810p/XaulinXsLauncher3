from pathlib import Path
import re

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

p = Path("res/values-v34/colors.xml")
if not p.exists():
    fail(f"não encontrei {p}")
    raise SystemExit(1)

content = p.read_text(encoding="utf-8")
count_fixed = 0
count_kept = 0

def replace_line(match):
    global count_fixed, count_kept
    full_line = match.group(0)
    name = match.group(1)
    value = match.group(2)
    if value == "@android:color/transparent":
        new_value = f"@android:color/{name}"
        count_fixed += 1
        return full_line.replace(value, new_value)
    else:
        count_kept += 1
        return full_line

pattern = re.compile(r'<color name="([^"]+)">([^<]+)</color>')
new_content = pattern.sub(replace_line, content)
p.write_text(new_content, encoding="utf-8")
ok(f"{count_fixed} cores restauradas")
skip(f"{count_kept} linhas mantidas")
