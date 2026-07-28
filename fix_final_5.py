from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

# 1) build.gradle: corrigir o escaping do ACCESS_LAUNCHER_DATA
p = Path("build.gradle")
content = p.read_text(encoding="utf-8")
old = 'buildConfigField "String", "ACCESS_LAUNCHER_DATA", "com.android.launcher3.permission.ACCESS_LAUNCHER_DATA"'
new = 'buildConfigField "String", "ACCESS_LAUNCHER_DATA", "\\"com.android.launcher3.permission.ACCESS_LAUNCHER_DATA\\""'
if new in content:
    skip("build.gradle: ACCESS_LAUNCHER_DATA já corrigido")
elif old in content:
    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")
    ok("build.gradle: ACCESS_LAUNCHER_DATA agora é string literal de verdade")
else:
    fail("build.gradle: linha não bateu (confere manualmente)")

# 2) IconProvider.java: import de R faltando
p = Path("iconloader/src/com/android/launcher3/icons/IconProvider.java")
content = p.read_text(encoding="utf-8")
if "import com.android.launcher3.R;" in content:
    skip("IconProvider.java: já tem o import")
else:
    lines = content.split("\n")
    pkg_idx = next(i for i, l in enumerate(lines) if l.startswith("package "))
    lines.insert(pkg_idx + 1, "\nimport com.android.launcher3.R;")
    p.write_text("\n".join(lines), encoding="utf-8")
    ok("IconProvider.java: import com.android.launcher3.R adicionado")

# 3) android/appwidget/flags/Flags.java
stub_dir = Path("aosp-stubs/android/appwidget/flags")
stub_dir.mkdir(parents=True, exist_ok=True)
stub_file = stub_dir / "Flags.java"
if stub_file.exists():
    skip("android/appwidget/flags/Flags.java já existe")
else:
    stub_file.write_text(
        "package android.appwidget.flags;\n\n"
        "/** Stub manual — flags do AppWidgetManager (preview gerado), API recente. */\n"
        "public final class Flags {\n"
        "    private Flags() {}\n\n"
        "    public static boolean generatedPreviews() { return false; }\n"
        "}\n",
        encoding="utf-8",
    )
    ok("android/appwidget/flags/Flags.java criado")

print("\nScript concluído.")
