from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

p = Path("src/com/android/launcher3/dagger/LauncherAppModule.kt")
content = p.read_text(encoding="utf-8")

old = (
    "            WidgetModule::class,\n"
    "            StatsLoggerModule::class,\n"
    "            OrganizerLauncherModule::class,\n"
    "        ]\n"
    ")\n"
    "class BootUnsafeModules"
)
new = (
    "            WidgetModule::class,\n"
    "            StatsLoggerModule::class,\n"
    "            OrganizerLauncherModule::class,\n"
    "            LauncherWidgetPickerModule::class,\n"
    "            WorkspaceFunctionsLauncherModule::class,\n"
    "        ]\n"
    ")\n"
    "class BootUnsafeModules"
)

if "LauncherWidgetPickerModule::class" in content:
    skip("módulos já incluídos")
elif old in content:
    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")
    ok("módulos incluídos em BootUnsafeModules")
else:
    fail("não achei o bloco de BootUnsafeModules")

p2 = Path("src/com/android/launcher3/dagger/LauncherBaseAppComponent.java")
content2 = p2.read_text(encoding="utf-8")

if "WidgetPickerComposeWrapper" in content2:
    skip("já exposto")
else:
    old_import_anchor = "import com.android.launcher3.widget.util.WidgetSizeHandler;\n"
    new_import = (
        "import com.android.launcher3.widget.util.WidgetSizeHandler;\n"
        "import com.android.launcher3.widgetpicker.WidgetPickerComposeWrapper;\n"
    )
    content2 = content2.replace(old_import_anchor, new_import, 1)

    old_method_anchor = "    GridSizeMigrationLogic createNewGridSizeMigrationLogic();"
    new_method = (
        "    GridSizeMigrationLogic createNewGridSizeMigrationLogic();\n\n"
        "    /** Wrapper that bootstraps the compose-based widget picker UI */\n"
        "    WidgetPickerComposeWrapper getWidgetPickerComposeWrapper();"
    )
    content2 = content2.replace(old_method_anchor, new_method, 1)

    p2.write_text(content2, encoding="utf-8")
    ok("getWidgetPickerComposeWrapper() exposto")
