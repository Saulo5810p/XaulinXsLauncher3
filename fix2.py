import re
from pathlib import Path

root = Path(".")

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

# 1) build.gradle: buildConfigField pros campos customizados + exclusão robusta
#    do LauncherWidgetPickerModule.kt (além do WorkspaceFunctionsLauncherModule.kt,
#    que reaplicamos com regex mais tolerante dessa vez)
p = root / "build.gradle"
try:
    content = p.read_text(encoding="utf-8")

    # 1a) buildConfigField
    fields = [
        ('boolean', 'WIDGETS_ENABLED', 'true'),
        ('boolean', 'IS_STUDIO_BUILD', 'false'),
        ('String', 'ACCESS_LAUNCHER_DATA', '"com.android.launcher3.permission.ACCESS_LAUNCHER_DATA"'),
    ]
    anchor = 'versionName "1.0"\n'
    if anchor in content:
        added = []
        insert = ""
        for typ, name, val in fields:
            if f'"{name}"' in content or f"'{name}'" in content:
                continue
            insert += f'        buildConfigField "{typ}", "{name}", {val}\n'
            added.append(name)
        if insert:
            content = content.replace(anchor, anchor + insert, 1)
            ok(f"build.gradle: buildConfigField adicionados: {', '.join(added)}")
        else:
            skip("build.gradle: buildConfigField já existiam")
    else:
        fail("build.gradle: não achei 'versionName \"1.0\"' pra ancorar os buildConfigField (confere manualmente)")

    # 1b) exclusões — regex tolerante a espaçamento, insere logo antes de "res.srcDirs"
    #     dentro do bloco sourceSets.main
    excludes = [
        "com/android/launcher3/dagger/WorkspaceFunctionsLauncherModule.kt",
        "com/android/launcher3/widgetpicker/LauncherWidgetPickerModule.kt",
    ]
    for path_to_exclude in excludes:
        if path_to_exclude in content:
            skip(f"build.gradle já exclui {path_to_exclude}")
            continue
        m = re.search(r'\n(\s*)res\.srcDirs\s*=', content)
        if m:
            indent = m.group(1)
            line = f'{indent}java.exclude \'{path_to_exclude}\'\n'
            pos = m.start() + 1  # logo depois do \n
            content = content[:pos] + line + content[pos:]
            ok(f"build.gradle: exclusão de {path_to_exclude} adicionada")
        else:
            fail(f"build.gradle: não achei 'res.srcDirs' pra ancorar a exclusão de {path_to_exclude}")

    p.write_text(content, encoding="utf-8")
except FileNotFoundError:
    fail("build.gradle não encontrado (rode este script na raiz do projeto)")

# 2) Mais uma cor faltando
colors_path = root / "res" / "values" / "material_dynamic_colors_fallback.xml"
try:
    content = colors_path.read_text(encoding="utf-8")
    if 'name="materialColorOnTertiaryContainer"' in content:
        skip("material_dynamic_colors_fallback.xml já tem materialColorOnTertiaryContainer")
    else:
        line = '    <color name="materialColorOnTertiaryContainer">#31111D</color>\n'
        content = content.replace("</resources>", line + "</resources>", 1)
        colors_path.write_text(content, encoding="utf-8")
        ok("material_dynamic_colors_fallback.xml: materialColorOnTertiaryContainer adicionada")
except FileNotFoundError:
    fail(f"{colors_path} não encontrado")

# 3) Abandonar o alias de R (não funcionou) e corrigir os imports direto nos
#    arquivos do iconloader que usavam com.android.launcher3.icons.R
icons_dir = root / "iconloader" / "src" / "com" / "android" / "launcher3" / "icons"
for stale in ["R.kt", "R.java"]:
    fpath = icons_dir / stale
    if fpath.exists():
        fpath.unlink()
        ok(f"removido {fpath} (não precisamos mais do alias)")

fixed_files = []
for kt_file in root.glob("iconloader/src/**/*.kt"):
    text = kt_file.read_text(encoding="utf-8")
    new_text = text.replace(
        "import com.android.launcher3.icons.R",
        "import com.android.launcher3.R",
    )
    if new_text != text:
        kt_file.write_text(new_text, encoding="utf-8")
        fixed_files.append(str(kt_file))
if fixed_files:
    ok(f"import de R corrigido direto em {len(fixed_files)} arquivo(s): " + ", ".join(fixed_files))
else:
    skip("nenhum arquivo com 'import com.android.launcher3.icons.R' encontrado")

print("\nPronto. Roda:")
print("  ./gradlew --stop && ./gradlew assembleNoQuickstepDebug --stacktrace 2>&1 | tee build_next2.log")
