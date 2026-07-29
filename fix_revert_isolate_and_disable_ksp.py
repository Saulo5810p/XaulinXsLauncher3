from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

p = Path("src/com/android/launcher3/dagger/LauncherAppModule.kt")
content = p.read_text(encoding="utf-8")

old = "            // TESTE ISOLAMENTO: LauncherWidgetPickerModule::class,\n"
new = "            LauncherWidgetPickerModule::class,\n"

if new in content and old not in content:
    skip("já restaurado")
elif old in content:
    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")
    ok("LauncherWidgetPickerModule::class restaurado")

p2 = Path("build.gradle")
content2 = p2.read_text(encoding="utf-8")

old2 = "apply plugin: 'com.google.devtools.ksp'\n"
new2 = "// TESTE DIAGNOSTICO: apply plugin: 'com.google.devtools.ksp'\n"

if new2 in content2:
    skip("KSP já desativado")
elif old2 in content2:
    content2 = content2.replace(old2, new2, 1)
    p2.write_text(content2, encoding="utf-8")
    ok("plugin KSP comentado")
