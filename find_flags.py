from pathlib import Path

for p in Path(".").rglob("*.java"):
    if p.name == "Flags.java":
        content = p.read_text(encoding="utf-8", errors="ignore")
        has_method = "showHomeBehindDesktop" in content
        print(f"{'[TEM]' if has_method else '[FALTA]'} {p.resolve()}  ({len(content)} bytes)")

print("\n--- import de Flags no CheckLongPressHelper.java ---")
target = Path("src/com/android/launcher3/CheckLongPressHelper.java")
if target.exists():
    for line in target.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "import" in line and "Flags" in line:
            print(line)
else:
    print("CheckLongPressHelper.java não encontrado no caminho esperado")
