from pathlib import Path
import re

root = Path(".")

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")

# 1) Mover fisicamente os 3 arquivos do appfunctions/widgetpicker pra fora de
#    qualquer srcDir — o java.exclude do AGP não é respeitado pelo compilador
#    Kotlin de forma confiável, então exclusão por Gradle não helps aqui.
to_move = [
    root / "src/com/android/launcher3/dagger/WorkspaceFunctionsLauncherModule.kt",
    root / "src/com/android/launcher3/widgetpicker/LauncherWidgetPickerModule.kt",
    root / "src/com/android/launcher3/widgetpicker/WidgetPickerComposeWrapperImpl.kt",
]
archive_dir = root / "deferred-appfunctions-widgetpicker"
archive_dir.mkdir(exist_ok=True)
for f in to_move:
    if not f.exists():
        skip(f"{f} não existe (já movido antes?)")
        continue
    dest = archive_dir / f.name
    f.rename(dest)
    ok(f"movido {f} -> {dest}")

# 2) Adicionar "import com.android.launcher3.R" em arquivos do pacote
#    com.android.launcher3.icons que usam R.xxx sem nenhum import de R
fixed = []
for kt_file in root.glob("**/*.kt"):
    if "/build/" in str(kt_file) or "deferred-appfunctions-widgetpicker" in str(kt_file):
        continue
    text = kt_file.read_text(encoding="utf-8")
    if "package com.android.launcher3.icons" not in text:
        continue
    if "import com.android.launcher3.R" in text or "import com.android.launcher3.icons.R" in text:
        continue
    if not re.search(r'\bR\.(string|drawable|color|attr|dimen|layout|id|style|xml|array)\b', text):
        continue
    new_text = text.replace(
        "package com.android.launcher3.icons\n",
        "package com.android.launcher3.icons\n\nimport com.android.launcher3.R\n",
        1,
    )
    if new_text != text:
        kt_file.write_text(new_text, encoding="utf-8")
        fixed.append(str(kt_file))

if fixed:
    ok(f"import de R inserido em {len(fixed)} arquivo(s):")
    for f in fixed:
        print("   -", f)
else:
    skip("nenhum arquivo precisava do import de R inserido")

print("\nPronto. Roda:")
print("  ./gradlew --stop && ./gradlew assembleNoQuickstepDebug --stacktrace 2>&1 | tee build_next5.log")
