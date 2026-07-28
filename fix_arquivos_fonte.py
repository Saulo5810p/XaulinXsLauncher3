from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

# ============================================================
# 1) FastBitmapDrawable.kt — remover import errado de com.android.launcher3.R
#    (o arquivo só usa android.R.attr.*, nunca precisou do nosso R)
# ============================================================
p = Path("iconloader/src/com/android/launcher3/icons/FastBitmapDrawable.kt")
content = p.read_text(encoding="utf-8")
old = "import com.android.launcher3.R\n\nimport android.R\n"
new = "import android.R\n"
if "import com.android.launcher3.R" not in content:
    skip("FastBitmapDrawable.kt: import já estava correto")
elif old in content:
    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")
    ok("FastBitmapDrawable.kt: import com.android.launcher3.R removido")
else:
    fail("FastBitmapDrawable.kt: padrão de import não bateu exatamente (confere manualmente)")

# ============================================================
# 2) ApplicationInfoWrapper.kt — simplificar AppLock (API não existe em SDK pública)
# ============================================================
p = Path("src/com/android/launcher3/util/ApplicationInfoWrapper.kt")
content = p.read_text(encoding="utf-8")

old1 = (
    "    fun isAppLockSupported() =\n"
    "        android.security.Flags.appLockApis() && appInfo?.isAppLockSupported ?: false\n"
)
new1 = (
    "    // AppLock APIs (android.security.Flags.appLockApis() e\n"
    "    // ApplicationInfo.isAppLockSupported/isAppLockEnabled) ainda não existem\n"
    "    // em nenhuma SDK pública — desativado por enquanto.\n"
    "    fun isAppLockSupported() = false\n"
)
if "fun isAppLockSupported() = false" in content:
    skip("ApplicationInfoWrapper.kt: isAppLockSupported já simplificado")
elif old1 in content:
    content = content.replace(old1, new1, 1)
    ok("ApplicationInfoWrapper.kt: isAppLockSupported() simplificado")
else:
    fail("ApplicationInfoWrapper.kt: isAppLockSupported não bateu (confere manualmente)")

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
    fail("ApplicationInfoWrapper.kt: isAppLockEnabled não bateu (confere manualmente)")

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

new_block = '''        // TODO(Fase 2 - widgetpicker): o seletor visual de widgets está
        // desativado por enquanto (módulo widgetpicker adiado). Como fallback,
        // coloca o widget/atalho automaticamente em vez de mostrar a folha de
        // seleção de tamanho.
        dragLayer.postDelayed(
            { onPlaceAutomaticallyClick(null) },
            ACTIVITY_SLIDE_IN_DURATION_MS,
        )'''

if "onPlaceAutomaticallyClick(null) }," in content:
    skip("AddItemActivity.kt: bloco já substituído")
elif old_block in content:
    content = content.replace(old_block, new_block, 1)
    ok("AddItemActivity.kt: bloco do widget picker substituído pelo fallback automático")
else:
    fail("AddItemActivity.kt: bloco não bateu exatamente (confere manualmente)")

for old_import in [
    "import com.android.launcher3.widgetpicker.WidgetPickerConfig\n",
    "import com.android.launcher3.dagger.LauncherComponentProvider\n",
]:
    if old_import in content:
        content = content.replace(old_import, "", 1)
        ok(f"AddItemActivity.kt: import removido: {old_import.strip()}")

p.write_text(content, encoding="utf-8")

# ============================================================
# 4) WidgetVisibilityTracker.kt — desativar tracking (API ainda não existe)
# ============================================================
p = Path("src/com/android/launcher3/widget/WidgetVisibilityTracker.kt")
content = p.read_text(encoding="utf-8")

old = '''            if (inNormalState && noFloatingViews && pageIndex in visiblePages) {
                view.startVisibilityTracking()
            } else {
                view.stopVisibilityTracking()
            }'''

new = '''            // TODO: startVisibilityTracking()/stopVisibilityTracking() ainda não
            // existem na classe base do host view nessa árvore de código (ou são API
            // novíssima do Android 17 sem SDK pública ainda) — desativado por enquanto,
            // é só uma otimização de bateria/performance, não afeta a função do widget.
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
    ok("WidgetVisibilityTracker.kt: visibility tracking desativado (comentado)")
else:
    fail("WidgetVisibilityTracker.kt: bloco não bateu exatamente (confere manualmente)")

print("\nScript 2 concluído.")
