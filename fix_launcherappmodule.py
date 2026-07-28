from pathlib import Path

p = Path("src/com/android/launcher3/dagger/LauncherAppModule.kt")
content = p.read_text(encoding="utf-8")

replacements = [
    ("import com.android.launcher3.widgetpicker.LauncherWidgetPickerModule\n", ""),
    ("            LauncherWidgetPickerModule::class,\n", ""),
    ("            WorkspaceFunctionsLauncherModule::class,\n", ""),
]

for old, new in replacements:
    if old not in content:
        print(f"[SKIP] não achei: {old!r}")
        continue
    content = content.replace(old, new, 1)
    print(f"[OK] removido: {old!r}")

p.write_text(content, encoding="utf-8")
