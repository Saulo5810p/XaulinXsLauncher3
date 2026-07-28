from pathlib import Path

root = Path(".")
def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

# ============================================================
# 1) build.gradle
# ============================================================
p = root / "build.gradle"
content = p.read_text(encoding="utf-8")

# 1a) opt-in pras APIs experimentais do Compose
if "freeCompilerArgs" in content:
    skip("build.gradle já tem freeCompilerArgs")
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
        ok("build.gradle: freeCompilerArgs com opt-in adicionado")
    else:
        fail("build.gradle: não achei o bloco kotlinOptions original pra âncora do opt-in")

# 1b) graphics-shapes 1.0.1 -> 1.1.0
old_shapes = "implementation 'androidx.graphics:graphics-shapes:1.0.1'"
new_shapes = "implementation 'androidx.graphics:graphics-shapes:1.1.0'"
if new_shapes in content:
    skip("graphics-shapes já está em 1.1.0")
elif old_shapes in content:
    content = content.replace(old_shapes, new_shapes, 1)
    ok("graphics-shapes atualizado pra 1.1.0")
else:
    fail("não achei a linha do graphics-shapes 1.0.1 (confere manualmente)")

# 1c) compose-bom 2024.10.00 -> 2026.06.01
old_bom = "platform('androidx.compose:compose-bom:2024.10.00')"
new_bom = "platform('androidx.compose:compose-bom:2026.06.01')"
if new_bom in content:
    skip("compose-bom já está em 2026.06.01")
elif old_bom in content:
    content = content.replace(old_bom, new_bom, 1)
    ok("compose-bom atualizado pra 2026.06.01")
else:
    fail("não achei a linha do compose-bom 2024.10.00 (confere manualmente)")

# 1d) material-icons-extended
if "material-icons-extended" in content:
    skip("material-icons-extended já estava lá")
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
        fail("não achei a linha do material3 pra âncora do material-icons-extended")

p.write_text(content, encoding="utf-8")

# ============================================================
# 2) aosp-stubs/com/android/launcher3/Flags.java — 2 métodos
# ============================================================
flags_path = root / "aosp-stubs/com/android/launcher3/Flags.java"
if flags_path.exists():
    content = flags_path.read_text(encoding="utf-8")
    added = []
    for name in ["getEnableAppLockIntentForPackage", "enableTrashAndRestoreByFilePathApi"]:
        if name in content:
            continue
        line = f"    public static boolean {name}() {{ return false; }}\n"
        idx = content.rstrip().rfind("}")
        content = content[:idx].rstrip() + "\n" + line + "}\n"
        added.append(name)
    if added:
        flags_path.write_text(content, encoding="utf-8")
        ok(f"Flags.java: adicionados {', '.join(added)}")
    else:
        skip("Flags.java já tinha os dois métodos")
else:
    fail(f"{flags_path} não encontrado")

# ============================================================
# 3) aosp-stubs/com/android/wm/shell/Flags.java — enableGsf
# ============================================================
wm_flags = root / "aosp-stubs/com/android/wm/shell/Flags.java"
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
    fail(f"{wm_flags} NÃO EXISTE — roda: find . -path '*/wm/shell*' e me manda o resultado")

# ============================================================
# 4) mover PreviewContext.kt (suporte de @Preview, não essencial)
# ============================================================
preview_file = root / "src/com/android/launcher3/preview/PreviewContext.kt"
archive_dir = root / "deferred-appfunctions-widgetpicker"
archive_dir.mkdir(exist_ok=True)
if preview_file.exists():
    dest = archive_dir / preview_file.name
    preview_file.rename(dest)
    ok(f"movido {preview_file} -> {dest}")
else:
    skip(f"{preview_file} não existe (já movido antes?)")

print("\nScript 1 concluído.")
