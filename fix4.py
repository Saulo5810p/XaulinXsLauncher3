from pathlib import Path

root = Path(".")
archive_dir = root / "deferred-appfunctions-widgetpicker"
archive_dir.mkdir(exist_ok=True)

dirs_to_move = [
    root / "src/com/android/launcher3/widgetpicker",
    root / "src/com/android/launcher3/workspacefunctions",
]

for d in dirs_to_move:
    if not d.exists():
        print(f"[SKIP] {d} não existe (já movido antes?)")
        continue
    dest = archive_dir / d.name
    d.rename(dest)
    print(f"[OK] movido {d} -> {dest}")

print("\nAgora preciso ver o LauncherAppModule.kt (linhas ~40-60) pra tirar")
print("as referências a LauncherWidgetPickerModule/WorkspaceFunctionsLauncherModule")
print("da lista de módulos do @Component. Roda:")
print("  sed -n '1,70p' src/com/android/launcher3/dagger/LauncherAppModule.kt")
print("e me manda a saída.")
