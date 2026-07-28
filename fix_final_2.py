from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

# ============================================================
# 1) FastBitmapDrawable.kt — remover import errado de com.android.launcher3.R
# ============================================================
p = Path("iconloader/src/com/android/launcher3/icons/FastBitmapDrawable.kt")
content = p.read_text(encoding="utf-8")
old = "import com.android.launcher3.R\n\nimport android.R\n"
new = "import android.R\n"
if "import com.android.launcher3.R" not in content:
    skip("FastBitmapDrawable.kt: já estava correto")
elif old in content:
    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")
    ok("FastBitmapDrawable.kt: import corrigido")
else:
    fail("FastBitmapDrawable.kt: padrão não bateu (confere manualmente)")

# ============================================================
# 2) ApplicationInfoWrapper.kt — simplificar AppLock
# ============================================================
p = Path("src/com/android/launcher3/util/ApplicationInfoWrapper.kt")
content = p.read_text(encoding="utf-8")

old1 = (
    "    fun isAppLockSupported() =\n"
    "        android.security.Flags.appLockApis() && appInfo?.isAppLockSupported ?: false\n"
)
new1 = (
    "    // ApplicationInfo.isAppLockSupported/isAppLockEnabled ainda não existem\n"
    "    // em nenhuma SDK pública — desativado por enquanto.\n"
    "    fun isAppLockSupported() = false\n"
)
if "fun isAppLockSupported() = false" in content:
    skip("ApplicationInfoWrapper.kt: isAppLockSupported já simplificado")
elif old1 in content:
    content = content.replace(old1, new1, 1)
    ok("ApplicationInfoWrapper.kt: isAppLockSupported() simplificado")
else:
    fail("ApplicationInfoWrapper.kt: isAppLockSupported não bateu")

old2 = (
    "    fun isAppLockEnabled() =\n"
    "        android.security.Flags.appLockApis() && appInfo?.isAppLockEnabled ?: false\n"
)
new2 = "    fun isAppLockEnabled() = false\n"
if "fun isAppLockEnabled() = false" in content:
    skip("ApplicationInfoWrapper.kt: isAppLockEnabled já simplificado")
elif old2 in content:
    content = content.replace(old2, new2, 1)
    ok("ApplicationInfoWrapper.kt: isAppLockEnabled() simplificado")
else:
    fail("ApplicationInfoWrapper.kt: isAppLockEnabled não bateu")

p.write_text(content, encoding="utf-8")

# ============================================================
# 3) AddItemActivity.kt — fallback pro widget picker desativado
# ============================================================
p = Path("src/com/android/launcher3/dragndrop/AddItemActivity.kt")
content = p.read_text(encoding="utf-8")

old_block = '''        dragLayer.postDelayed(
            {
                LauncherComponentProvider.get(this)
                    .widgetPickerComposeWrapper
                    .showWidgetsForPinRequest(
                        activity = this,
                        targetApp = targetApp.toPackageUserKey(),
                        pinItemRequest = pinItemRequest,
                        widgetPickerConfig = WidgetPickerConfig(),
                        pinItemAddHandler = this,
                    )
            },
            ACTIVITY_SLIDE_IN_DURATION_MS,
        )'''

new_block = '''        // TODO(Fase 2 - widgetpicker): seletor visual desativado por enquanto.
        // Fallback: coloca o widget/atalho automaticamente.
        dragLayer.postDelayed(
            { onPlaceAutomaticallyClick(null) },
            ACTIVITY_SLIDE_IN_DURATION_MS,
        )'''

if "onPlaceAutomaticallyClick(null) }," in content:
    skip("AddItemActivity.kt: já substituído")
elif old_block in content:
    content = content.replace(old_block, new_block, 1)
    ok("AddItemActivity.kt: fallback aplicado")
else:
    fail("AddItemActivity.kt: bloco não bateu")

for old_import in [
    "import com.android.launcher3.widgetpicker.WidgetPickerConfig\n",
    "import com.android.launcher3.dagger.LauncherComponentProvider\n",
]:
    if old_import in content:
        content = content.replace(old_import, "", 1)
        ok(f"AddItemActivity.kt: import removido: {old_import.strip()}")

p.write_text(content, encoding="utf-8")

# ============================================================
# 4) WidgetVisibilityTracker.kt — desativar tracking
# ============================================================
p = Path("src/com/android/launcher3/widget/WidgetVisibilityTracker.kt")
content = p.read_text(encoding="utf-8")

old = '''            if (inNormalState && noFloatingViews && pageIndex in visiblePages) {
                view.startVisibilityTracking()
            } else {
                view.stopVisibilityTracking()
            }'''

new = '''            // Desativado: API ainda não existe nessa árvore / SDK.
            if (inNormalState && noFloatingViews && pageIndex in visiblePages) {
                // view.startVisibilityTracking()
            } else {
                // view.stopVisibilityTracking()
            }'''

if "// view.startVisibilityTracking()" in content:
    skip("WidgetVisibilityTracker.kt: já desativado")
elif old in content:
    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")
    ok("WidgetVisibilityTracker.kt: desativado")
else:
    fail("WidgetVisibilityTracker.kt: bloco não bateu")

# ============================================================
# 5) ModelProxyProvider.kt — ACCESS_LAUNCHER_DATA é do framework
#    (android.Manifest.permission), não existe publicamente. Troca por
#    uma constante local.
# ============================================================
p = Path("src/com/android/launcher3/model/ModelProxyProvider.kt")
content = p.read_text(encoding="utf-8")

old_import = "import android.Manifest.permission.ACCESS_LAUNCHER_DATA\n"
if "private const val ACCESS_LAUNCHER_DATA" in content:
    skip("ModelProxyProvider.kt: já corrigido")
elif old_import in content:
    # troca o import pela constante local, inserida logo após o pacote
    content = content.replace(old_import, "", 1)
    content = content.replace(
        "package com.android.launcher3.model\n",
        "package com.android.launcher3.model\n\n"
        '// android.Manifest.permission.ACCESS_LAUNCHER_DATA ainda não existe\n'
        '// em nenhuma SDK pública — usando um nome de permissão local por enquanto.\n'
        'private const val ACCESS_LAUNCHER_DATA = "com.android.launcher3.permission.ACCESS_LAUNCHER_DATA"\n',
        1,
    )
    p.write_text(content, encoding="utf-8")
    ok("ModelProxyProvider.kt: ACCESS_LAUNCHER_DATA corrigido (constante local)")
else:
    fail("ModelProxyProvider.kt: import não bateu (confere manualmente)")

print("\nScript 2 concluído.")
