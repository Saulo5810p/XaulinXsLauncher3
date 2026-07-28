from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

p = Path("src/com/android/launcher3/dagger/LauncherBaseAppComponent.java")
content = p.read_text(encoding="utf-8")

removals = [
    "import com.android.launcher3.appfunctions.workspace.WorkspaceAppFunctions;\n",
    "import com.android.launcher3.widgetpicker.WidgetPickerComposeWrapper;\n",
    "    WidgetPickerComposeWrapper getWidgetPickerComposeWrapper();\n",
    "    /** Returns the WorkspaceAppFunctions instance */\n    WorkspaceAppFunctions getWorkspaceAppFunctions();\n\n",
]

changed = False
for old in removals:
    if old in content:
        content = content.replace(old, "", 1)
        ok(f"removido: {old.strip()[:70]}")
        changed = True
    else:
        skip(f"não achei (já removido antes?): {old.strip()[:70]}")

if changed:
    p.write_text(content, encoding="utf-8")

print("\nPronto. Roda:")
print("  ./gradlew --stop && ./gradlew assembleNoQuickstepDebug --stacktrace 2>&1 | tee build_next14.log")
