from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

# ============================================================
# 1) ModelProxyProvider.kt — reconfirma o fix do import-order
#    (caso o comando anterior não tenha rodado ainda)
# ============================================================
p = Path("src/com/android/launcher3/model/ModelProxyProvider.kt")
content = p.read_text(encoding="utf-8")
bad = (
    "package com.android.launcher3.model\n\n"
    "// android.Manifest.permission.ACCESS_LAUNCHER_DATA ainda não existe\n"
    "// em nenhuma SDK pública — usando um nome de permissão local por enquanto.\n"
    'private const val ACCESS_LAUNCHER_DATA = "com.android.launcher3.permission.ACCESS_LAUNCHER_DATA"\n'
)
if bad in content:
    content = content.replace(bad, "package com.android.launcher3.model\n", 1)
    lines = content.split("\n")
    last_import_idx = max(i for i, l in enumerate(lines) if l.startswith("import "))
    const_lines = [
        "",
        "// android.Manifest.permission.ACCESS_LAUNCHER_DATA ainda não existe",
        "// em nenhuma SDK pública — usando um nome de permissão local por enquanto.",
        'private const val ACCESS_LAUNCHER_DATA = "com.android.launcher3.permission.ACCESS_LAUNCHER_DATA"',
    ]
    lines = lines[: last_import_idx + 1] + const_lines + lines[last_import_idx + 1 :]
    p.write_text("\n".join(lines), encoding="utf-8")
    ok("ModelProxyProvider.kt: constante movida pra depois dos imports")
elif "private const val ACCESS_LAUNCHER_DATA" in content:
    skip("ModelProxyProvider.kt: já estava corrigido")
else:
    fail("ModelProxyProvider.kt: padrão não bateu (confere manualmente)")

# ============================================================
# 2) WorkspaceItemProcessor.kt — alias pro wm.shell.Flags
# ============================================================
p = Path("src/com/android/launcher3/model/WorkspaceItemProcessor.kt")
content = p.read_text(encoding="utf-8")
if "import com.android.wm.shell.Flags as WmShellFlags" in content:
    skip("WorkspaceItemProcessor.kt: já usa o alias")
else:
    content = content.replace(
        "import com.android.launcher3.provider.LauncherDbUtils.asSequence\n",
        "import com.android.launcher3.provider.LauncherDbUtils.asSequence\n"
        "import com.android.wm.shell.Flags as WmShellFlags\n",
        1,
    )
    content = content.replace(
        "com.android.wm.shell.Flags.enable2x1Split()",
        "WmShellFlags.enable2x1Split()",
        1,
    )
    p.write_text(content, encoding="utf-8")
    ok("WorkspaceItemProcessor.kt: import + alias adicionados")

# ============================================================
# 3) PopupContainerWithArrow.kt — alias pro wm.shell.Flags
# ============================================================
p = Path("src/com/android/launcher3/popup/PopupContainerWithArrow.kt")
content = p.read_text(encoding="utf-8")
if "import com.android.wm.shell.Flags as WmShellFlags" in content:
    skip("PopupContainerWithArrow.kt: já usa o alias")
else:
    # insere o import logo depois do "package ..." (primeira linha não-comentário/licença)
    lines = content.split("\n")
    pkg_idx = next(i for i, l in enumerate(lines) if l.startswith("package "))
    lines.insert(pkg_idx + 1, "\nimport com.android.wm.shell.Flags as WmShellFlags")
    content = "\n".join(lines)
    content = content.replace(
        "com.android.wm.shell.Flags.enableGsf()",
        "WmShellFlags.enableGsf()",
        1,
    )
    p.write_text(content, encoding="utf-8")
    ok("PopupContainerWithArrow.kt: import + alias adicionados")

# ============================================================
# 4) WorkspaceProfile.kt — alias pro systemui.shared.Flags
# ============================================================
p = Path("src/com/android/launcher3/deviceprofile/WorkspaceProfile.kt")
content = p.read_text(encoding="utf-8")
if "import com.android.systemui.shared.Flags as SystemUiSharedFlags" in content:
    skip("WorkspaceProfile.kt: já usa o alias")
else:
    lines = content.split("\n")
    pkg_idx = next(i for i, l in enumerate(lines) if l.startswith("package "))
    lines.insert(pkg_idx + 1, "\nimport com.android.systemui.shared.Flags as SystemUiSharedFlags")
    content = "\n".join(lines)
    content = content.replace(
        "com.android.systemui.shared.Flags.workspaceItemsLabelHidden()",
        "SystemUiSharedFlags.workspaceItemsLabelHidden()",
        1,
    )
    p.write_text(content, encoding="utf-8")
    ok("WorkspaceProfile.kt: import + alias adicionados")

# ============================================================
# 5) AppLockShortcut.kt — getEnableAppLockIntentForPackage é método de
#    PackageManager (framework, API nova demais), não do Flags. Criamos
#    uma extensão Kotlin no lugar.
# ============================================================
ext_dir = Path("aosp-stubs/android/content/pm")
ext_dir.mkdir(parents=True, exist_ok=True)
ext_file = ext_dir / "PackageManagerAppLockExt.kt"
if ext_file.exists():
    skip("PackageManagerAppLockExt.kt já existe")
else:
    ext_file.write_text(
        "package android.content.pm\n\n"
        "import android.app.PendingIntent\n\n"
        "/**\n"
        " * Stub manual — getEnableAppLockIntentForPackage() é um método novo do\n"
        " * PackageManager (recurso de AppLock) que ainda não existe em SDK pública.\n"
        " */\n"
        "fun PackageManager.getEnableAppLockIntentForPackage(\n"
        "    packageName: String,\n"
        "    enable: Boolean,\n"
        "): PendingIntent? = null\n",
        encoding="utf-8",
    )
    ok("PackageManagerAppLockExt.kt criado")

p = Path("src/com/android/launcher3/popup/AppLockShortcut.kt")
content = p.read_text(encoding="utf-8")
if "import android.content.pm.getEnableAppLockIntentForPackage" in content:
    skip("AppLockShortcut.kt: import já presente")
else:
    content = content.replace(
        "import android.app.PendingIntent\n",
        "import android.app.PendingIntent\n"
        "import android.content.pm.getEnableAppLockIntentForPackage\n",
        1,
    )
    p.write_text(content, encoding="utf-8")
    ok("AppLockShortcut.kt: import da extensão adicionado")

# ============================================================
# 6) build.gradle — adicionar animationlib/src ao sourceSet
# ============================================================
p = Path("build.gradle")
content = p.read_text(encoding="utf-8")
if "'animationlib/src'" in content:
    skip("build.gradle já tem animationlib/src")
else:
    anchor = "'iconloader/src',"
    if anchor in content:
        content = content.replace(anchor, anchor + "\n                'animationlib/src',", 1)
        p.write_text(content, encoding="utf-8")
        ok("build.gradle: animationlib/src adicionado ao java.srcDirs")
    else:
        fail("build.gradle: não achei a linha 'iconloader/src' pra âncora")

print("\nScript concluído.")
