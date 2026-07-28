from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

# ============================================================
# 1) build.gradle
# ============================================================
p = Path("build.gradle")
content = p.read_text(encoding="utf-8")

if "freeCompilerArgs" in content:
    skip("freeCompilerArgs já existe")
else:
    anchor = '    kotlinOptions {\n        jvmTarget = "17"\n    }'
    replacement = (
        '    kotlinOptions {\n'
        '        jvmTarget = "17"\n'
        '        freeCompilerArgs += [\n'
        '            "-opt-in=androidx.compose.foundation.ExperimentalFoundationApi",\n'
        '            "-opt-in=androidx.compose.foundation.layout.ExperimentalLayoutApi",\n'
        '            "-opt-in=androidx.compose.material3.ExperimentalMaterial3Api",\n'
        '            "-opt-in=androidx.compose.ui.ExperimentalComposeUiApi",\n'
        '        ]\n'
        '    }'
    )
    if anchor in content:
        content = content.replace(anchor, replacement, 1)
        ok("freeCompilerArgs (opt-in Compose) adicionado")
    else:
        fail("não achei o bloco kotlinOptions original")

old_shapes = "implementation 'androidx.graphics:graphics-shapes:1.0.1'"
new_shapes = "implementation 'androidx.graphics:graphics-shapes:1.1.0'"
if new_shapes in content:
    skip("graphics-shapes já em 1.1.0")
elif old_shapes in content:
    content = content.replace(old_shapes, new_shapes, 1)
    ok("graphics-shapes -> 1.1.0")
else:
    fail("não achei a linha do graphics-shapes 1.0.1")

old_bom = "platform('androidx.compose:compose-bom:2024.10.00')"
new_bom = "platform('androidx.compose:compose-bom:2026.06.01')"
if new_bom in content:
    skip("compose-bom já em 2026.06.01")
elif old_bom in content:
    content = content.replace(old_bom, new_bom, 1)
    ok("compose-bom -> 2026.06.01")
else:
    fail("não achei a linha do compose-bom 2024.10.00")

if "material-icons-extended" in content:
    skip("material-icons-extended já presente")
else:
    anchor2 = "implementation 'androidx.compose.material3:material3'"
    if anchor2 in content:
        content = content.replace(
            anchor2,
            anchor2 + "\n    implementation 'androidx.compose.material:material-icons-extended'",
            1,
        )
        ok("material-icons-extended adicionado")
    else:
        fail("não achei a linha do material3")

if "activity-compose" in content:
    skip("activity-compose já presente")
else:
    anchor3 = "implementation 'androidx.navigation:navigation-compose:2.8.3'"
    if anchor3 in content:
        content = content.replace(
            anchor3,
            anchor3 + "\n    implementation 'androidx.activity:activity-compose:1.10.0'",
            1,
        )
        ok("activity-compose:1.10.0 adicionado (LocalActivity)")
    else:
        fail("não achei a linha do navigation-compose")

p.write_text(content, encoding="utf-8")

# ============================================================
# 2) aosp-stubs/com/android/launcher3/Flags.java — 0 métodos novos
#    (getEnableAppLockIntentForPackage e enableTrashAndRestoreByFilePathApi
#    NÃO são dessa classe, descobrimos depois — vão nos stubs certos abaixo)
# ============================================================

# ============================================================
# 3) aosp-stubs/com/android/wm/shell/Flags.java — enableGsf
# ============================================================
wm_flags = Path("aosp-stubs/com/android/wm/shell/Flags.java")
if wm_flags.exists():
    content = wm_flags.read_text(encoding="utf-8")
    if "enableGsf" in content:
        skip("wm/shell/Flags.java já tem enableGsf()")
    else:
        idx = content.rstrip().rfind("}")
        content = content[:idx].rstrip() + "\n    public static boolean enableGsf() { return false; }\n}\n"
        wm_flags.write_text(content, encoding="utf-8")
        ok("wm/shell/Flags.java: enableGsf() adicionado")
else:
    fail(f"{wm_flags} não existe")

# ============================================================
# 4) android/security/Flags.java — AppLock
# ============================================================
sec_dir = Path("aosp-stubs/android/security")
sec_dir.mkdir(parents=True, exist_ok=True)
sec_flags = sec_dir / "Flags.java"
if sec_flags.exists():
    skip("android/security/Flags.java já existe")
else:
    sec_flags.write_text(
        "package android.security;\n\n"
        "/** Stub manual — API de AppLock, recurso recente demais pra SDK pública. */\n"
        "public final class Flags {\n"
        "    private Flags() {}\n\n"
        "    public static boolean appLockApis() { return false; }\n\n"
        "    public static String getEnableAppLockIntentForPackage(String packageName) {\n"
        "        return null;\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    ok("android/security/Flags.java criado")

# ============================================================
# 5) com/android/providers/media/flags/Flags.java
# ============================================================
media_dir = Path("aosp-stubs/com/android/providers/media/flags")
media_dir.mkdir(parents=True, exist_ok=True)
media_flags = media_dir / "Flags.java"
if media_flags.exists():
    skip("providers/media/flags/Flags.java já existe")
else:
    media_flags.write_text(
        "package com.android.providers.media.flags;\n\n"
        "/** Stub manual — flags do MediaProvider usadas por HomeScreenFilesUtils. */\n"
        "public final class Flags {\n"
        "    private Flags() {}\n\n"
        "    public static boolean enableTrashAndRestoreByFilePathApi() { return false; }\n"
        "}\n",
        encoding="utf-8",
    )
    ok("providers/media/flags/Flags.java criado")

# ============================================================
# 6) com/android/systemui/shared/Flags.java
# ============================================================
sysui_dir = Path("aosp-stubs/com/android/systemui/shared")
sysui_dir.mkdir(parents=True, exist_ok=True)
sysui_flags = sysui_dir / "Flags.java"
if sysui_flags.exists():
    skip("systemui/shared/Flags.java já existe")
else:
    sysui_flags.write_text(
        "package com.android.systemui.shared;\n\n"
        "/** Stub manual — flags compartilhadas da SystemUI usadas pelo Launcher3. */\n"
        "public final class Flags {\n"
        "    private Flags() {}\n\n"
        "    public static boolean workspaceItemsLabelHidden() { return false; }\n"
        "}\n",
        encoding="utf-8",
    )
    ok("systemui/shared/Flags.java criado")

# ============================================================
# 7) com/android/launcher3/RoundRectEstimator.java — classe própria
#    do projeto que está faltando (não é do androidx.graphics.shapes!)
# ============================================================
rre_path = Path("aosp-stubs/com/android/launcher3/RoundRectEstimator.java")
if rre_path.exists():
    skip("RoundRectEstimator.java já existe")
else:
    rre_path.write_text(
        "package com.android.launcher3;\n\n"
        "import android.graphics.Path;\n\n"
        "/**\n"
        " * Stub manual — classe própria do Launcher3 que está faltando nessa árvore\n"
        " * (não é do androidx.graphics.shapes). O algoritmo real estima o quão perto\n"
        " * um Path está de ser um retângulo arredondado; sempre retornando -1 aqui\n"
        " * desativa essa otimização e força o ShapeDelegate a usar sempre o path\n"
        " * genérico como fallback — funcionalmente seguro, só não é a forma\n"
        " * \"perfeita\" de ícone.\n"
        " */\n"
        "public final class RoundRectEstimator {\n"
        "    private RoundRectEstimator() {}\n\n"
        "    public static float estimateRadius(Path path, float pathSize) {\n"
        "        return -1f;\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    ok("RoundRectEstimator.java criado (stub)")

# ============================================================
# 8) mover PreviewContext.kt
# ============================================================
preview_file = Path("src/com/android/launcher3/preview/PreviewContext.kt")
archive_dir = Path("deferred-appfunctions-widgetpicker")
archive_dir.mkdir(exist_ok=True)
if preview_file.exists():
    preview_file.rename(archive_dir / preview_file.name)
    ok(f"movido {preview_file}")
else:
    skip(f"{preview_file} não existe (já movido?)")

print("\nScript 1 concluído.")
