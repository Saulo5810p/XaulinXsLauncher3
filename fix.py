import re
from pathlib import Path

root = Path(".")

def ok(msg):
    print(f"[OK] {msg}")

def skip(msg):
    print(f"[SKIP] {msg}")

def fail(msg):
    print(f"[FALHOU] {msg}")

# 1) build.gradle: adicionar buildFeatures { buildConfig true } (resolve BuildConfig)
p = root / "build.gradle"
try:
    content = p.read_text(encoding="utf-8")
    if "buildFeatures" in content and "buildConfig" in content:
        skip("build.gradle já tem buildFeatures { buildConfig }")
    else:
        anchor = '    kotlinOptions {\n        jvmTarget = "17"\n    }\n}'
        replacement = ('    kotlinOptions {\n        jvmTarget = "17"\n    }\n\n'
                       '    buildFeatures {\n        buildConfig true\n    }\n}')
        if anchor in content:
            content = content.replace(anchor, replacement, 1)
            p.write_text(content, encoding="utf-8")
            ok("build.gradle: buildFeatures { buildConfig true } adicionado")
        else:
            fail("build.gradle: não achei o bloco kotlinOptions pra ancorar (confere manualmente)")
except FileNotFoundError:
    fail("build.gradle não encontrado (rode este script na raiz do projeto)")

# 2) build.gradle: excluir WorkspaceFunctionsLauncherModule.kt do sourceSet
try:
    content = p.read_text(encoding="utf-8")
    exclude_line = "            java.exclude 'com/android/launcher3/dagger/WorkspaceFunctionsLauncherModule.kt'\n"
    if "WorkspaceFunctionsLauncherModule" in content:
        skip("build.gradle já exclui WorkspaceFunctionsLauncherModule.kt")
    else:
        anchor = "            res.srcDirs = [\n                'res',"
        if anchor in content:
            content = content.replace(anchor, exclude_line + anchor, 1)
            p.write_text(content, encoding="utf-8")
            ok("build.gradle: exclusão do WorkspaceFunctionsLauncherModule.kt adicionada")
        else:
            fail("build.gradle: não achei onde inserir a exclusão (confere manualmente)")
except FileNotFoundError:
    pass

# 3) Flags.java: adicionar os métodos que faltam
flags_path = root / "aosp-stubs" / "com" / "android" / "launcher3" / "Flags.java"
new_methods = [
    "getEnableAppLockIntentForPackage",
    "enableHomeScreenFilesCopyPaste",
    "enableHomeScreenFilesRenaming",
]
try:
    content = flags_path.read_text(encoding="utf-8")
    added = []
    for name in new_methods:
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
        skip("Flags.java já tem todos os métodos novos")
except FileNotFoundError:
    fail(f"{flags_path} não encontrado")

# 4) material_dynamic_colors_fallback.xml: adicionar as cores que faltam
colors_path = root / "res" / "values" / "material_dynamic_colors_fallback.xml"
new_colors = {
    "materialColorTertiary": "#7D5260",
    "materialColorOnTertiaryFixed": "#31111D",
    "materialColorTertiaryFixedDim": "#EFB8C8",
    "materialColorSurfaceVariant": "#E7E0EC",
    "materialColorOnTertiary": "#FFFFFF",
}
try:
    content = colors_path.read_text(encoding="utf-8")
    added = []
    for name, value in new_colors.items():
        if f'name="{name}"' in content:
            continue
        line = f'    <color name="{name}">{value}</color>\n'
        content = content.replace("</resources>", line + "</resources>", 1)
        added.append(name)
    if added:
        colors_path.write_text(content, encoding="utf-8")
        ok(f"material_dynamic_colors_fallback.xml: adicionadas {', '.join(added)}")
    else:
        skip("material_dynamic_colors_fallback.xml já tem todas as cores novas")
except FileNotFoundError:
    fail(f"{colors_path} não encontrado")

# 5) iconloader R.kt: trocar a classe Java (que não expõe as classes aninhadas
#    direito) por um typealias Kotlin
icons_dir = root / "iconloader" / "src" / "com" / "android" / "launcher3" / "icons"
r_java = icons_dir / "R.java"
r_kt = icons_dir / "R.kt"
if r_kt.exists():
    skip("iconloader/.../icons/R.kt já existe")
else:
    icons_dir.mkdir(parents=True, exist_ok=True)
    r_kt.write_text(
        "package com.android.launcher3.icons\n\n"
        "typealias R = com.android.launcher3.R\n",
        encoding="utf-8",
    )
    ok("iconloader/.../icons/R.kt criado (typealias)")
    if r_java.exists():
        r_java.unlink()
        ok("iconloader/.../icons/R.java antigo removido (substituído pelo R.kt)")

print("\nPronto. Roda:")
print("  ./gradlew --stop && ./gradlew assembleNoQuickstepDebug --stacktrace 2>&1 | tee build_next.log")
