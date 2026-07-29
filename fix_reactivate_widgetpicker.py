from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

p = Path("build.gradle")
content = p.read_text(encoding="utf-8")
original = content

old1 = "                // 'modules/appfunctions/src',\n"
new1 = "                'modules/appfunctions/src',\n"
if new1 in content:
    skip("modules/appfunctions/src já ativo")
elif old1 in content:
    content = content.replace(old1, new1, 1)
    ok("modules/appfunctions/src reativado")

old2 = "                // 'modules/widgetpicker/src',\n"
new2 = "                'deferred-appfunctions-widgetpicker',\n"
if new2 in content:
    skip("widgetpicker já ativo")
elif old2 in content:
    content = content.replace(old2, new2, 1)
    ok("deferred-appfunctions-widgetpicker reativado")

for old in [
    "            java.exclude 'com/android/launcher3/dagger/WorkspaceFunctionsLauncherModule.kt'\n",
    "            java.exclude 'com/android/launcher3/widgetpicker/LauncherWidgetPickerModule.kt'\n",
    "            java.exclude 'com/android/launcher3/widgetpicker/WidgetPickerComposeWrapperImpl.kt'\n",
]:
    if old in content:
        content = content.replace(old, "", 1)
        ok(f"exclude removido: {old.strip()}")

if content != original:
    p.write_text(content, encoding="utf-8")
    ok("build.gradle salvo")
