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
    for c in candidates:
        content = c.read_text(encoding="utf-8", errors="ignore")
        if "Archiving" in content or "archiving" in content:
            print(f"  candidato parecido: {c}")
    raise SystemExit(1)

content = target.read_text(encoding="utf-8")
print(f"--- Flags.java alvo: {target} ---")

pattern = re.compile(
    r'(public\s+static\s+boolean\s+enableSupportForArchiving\s*\(\s*\)\s*\{\s*return\s+)(false|true)(\s*;\s*\})'
)
m = pattern.search(content)
if not m:
    fail("não encontrei o padrão exato do método — mostrando linha bruta:")
    for line in content.splitlines():
        if "enableSupportForArchiving" in line:
            print(f"  > {line}")
    raise SystemExit(1)

if m.group(2) == "true":
    skip("enableSupportForArchiving() já retorna true")
else:
    new_content = content[:m.start()] + m.group(1) + "true" + m.group(3) + content[m.end():]
    target.write_text(new_content, encoding="utf-8")
    ok(f"enableSupportForArchiving() alterado de false para true em {target}")

print("\nScript concluído.")
