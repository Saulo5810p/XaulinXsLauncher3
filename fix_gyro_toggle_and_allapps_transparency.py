#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XaulinXs Customizations — script de CORREÇÃO (roda depois do
apply_gyro_toggle_and_allapps_transparency.py).

Corrige os 2 bugs reportados após o teste real no aparelho:

  1) Interruptor de giroscópio não desativava a inclinação na hora.
     Causa raiz: unregister() zerava tiltX/tiltY diretamente, mas a
     SpringAnimation continuava seu próprio loop de física e
     sobrescrevia esses valores de volta a cada frame (ela só para
     quando convergir ao alvo antigo, que nunca foi resetado). Fix:
     cancel() nas 2 SpringAnimation + zera o alvo (finalPosition)
     também. Além disso, como o coverflow só recalcula em eventos de
     scroll real (onScrollChanged), adicionado um hook para forçar
     reaplicação imediata do efeito no Workspace ao ligar/desligar o
     interruptor, sem precisar arrastar a tela.

  2) Transparência do menu de apps não tinha efeito nenhum, ficava
     sempre opaco. Causa raiz: existe uma camada opaca separada
     (ActivityAllAppsContainerView.getBackgroundColor(), pintada por
     cima de tudo em drawOnScrimWithScaleAndBottomOffset) que é
     totalmente independente do AllAppsState.getWorkspaceScrimColor()/
     WallpaperScrimHelper mexido no script anterior — aquele ficava
     "embaixo" e nunca aparecia. Fix: aplica o alpha do slider
     diretamente nessa camada real.

PRÉ-REQUISITO: rode antes o apply_gyro_toggle_and_allapps_transparency.py
(este script assume que os arquivos/patches dele já foram aplicados).

Idempotente — pode rodar várias vezes sem duplicar nada.

Uso (a partir da raiz do checkout):
    python3 fix_gyro_toggle_and_allapps_transparency.py
"""

import hashlib
import sys
from pathlib import Path

ROOT = Path.cwd()


def fail(msg: str) -> None:
    print(f"[ERRO] {msg}")
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def skip(msg: str) -> None:
    print(f"[SKIP] {msg}")


def patch_file(rel_path: str, marker: str, old: str, new: str, label: str) -> None:
    path = ROOT / rel_path
    if not path.exists():
        fail(f"{rel_path} não encontrado — checkout inesperado, abortando.")
    content = path.read_text(encoding="utf-8")
    if marker in content:
        skip(f"{label} (marcador já presente em {rel_path})")
        return
    count = content.count(old)
    if count == 0:
        fail(
            f"{label}: trecho esperado não encontrado em {rel_path}. "
            "Este script pressupõe que apply_gyro_toggle_and_allapps_transparency.py "
            "já foi rodado antes. Se já rodou e o erro persiste, o arquivo pode "
            "ter mudado — não vou aplicar às cegas."
        )
    if count > 1:
        fail(
            f"{label}: trecho esperado aparece {count} vezes em {rel_path} "
            "(deveria ser único) — abortando."
        )
    path.write_text(content.replace(old, new, 1), encoding="utf-8")
    ok(f"{label} ({rel_path})")


# ---------------------------------------------------------------------------
# Fix 1: giroscópio não desativava
# ---------------------------------------------------------------------------

def fix_gyro_toggle() -> None:
    rel = "src/com/xaulinxs/customizations/cinematic/GyroTiltProvider.kt"
    marker = "XAULINXS_GYRO_PROVIDER_SPRING_CANCEL_FIX"

    old_unregister = '''    private fun unregister() {
        sensorManager?.unregisterListener(sensorListener)
        listenerRegistered = false
        tiltX = 0f
        tiltY = 0f
        rawTiltX = 0f
        rawTiltY = 0f
    }
}

// XAULINXS_GYRO_PROVIDER_FILE
// XAULINXS_GYRO_PROVIDER_TOGGLE_SUPPORT'''

    new_unregister = '''    private fun unregister() {
        sensorManager?.unregisterListener(sensorListener)
        listenerRegistered = false
        // XaulinXs Customizations: zerar tiltX/tiltY diretamente NÃO bastava
        // — a SpringAnimation continua rodando seu próprio loop de física
        // (via Choreographer interno da lib androidx.dynamicanimation) até
        // convergir ao finalPosition antigo, e o addUpdateListener dela
        // sobrescrevia tiltX/tiltY de volta a cada frame, revertendo o
        // reset abaixo — por isso desligar o interruptor não desativava a
        // inclinação na hora. Fix: cancel() para o spring imediatamente
        // (sem mais updates) e zera o alvo (finalPosition) também, para
        // que uma eventual reativação comece do repouso em vez de
        // "perseguir" um ângulo antigo residual.
        springX.cancel()
        springY.cancel()
        springX.spring.finalPosition = 0f
        springY.spring.finalPosition = 0f
        tiltX = 0f
        tiltY = 0f
        rawTiltX = 0f
        rawTiltY = 0f
    }
}

// XAULINXS_GYRO_PROVIDER_FILE
// XAULINXS_GYRO_PROVIDER_TOGGLE_SUPPORT
// XAULINXS_GYRO_PROVIDER_SPRING_CANCEL_FIX'''

    patch_file(rel, marker, old_unregister, new_unregister,
               "GyroTiltProvider: cancelar SpringAnimation ao desligar")

    marker2 = "XAULINXS_GYRO_PROVIDER_REAPPLY_HOOK"
    old_notify = '''    fun notifySettingChanged(context: Context, enabled: Boolean) {
        if (!enabled) {
            unregister()
            return
        }
        val anyView = subscribedViews.firstOrNull() ?: return
        ensureRegistered(anyView.context)
    }'''

    new_notify = '''    fun notifySettingChanged(context: Context, enabled: Boolean) {
        if (!enabled) {
            unregister()
        } else {
            val anyView = subscribedViews.firstOrNull()
            if (anyView != null) ensureRegistered(anyView.context)
        }
        // XaulinXs Customizations: força a reaplicação imediata do
        // coverflow nas Workspaces inscritas, tanto ao desligar (mostra a
        // rotação zerada na hora, sem esperar o próximo scroll) quanto ao
        // ligar de novo (evita a página ficar "presa" no ângulo neutro até
        // o próximo gesto). // XAULINXS_GYRO_PROVIDER_REAPPLY_HOOK
        subscribedViews.forEach { view ->
            (view as? com.android.launcher3.Workspace<*>)?.xaulinXsReapplyCoverFlow()
        }
    }'''

    patch_file(rel, marker2, old_notify, new_notify,
               "GyroTiltProvider: reaplicar coverflow imediatamente no toggle")


def fix_workspace_reapply_hook() -> None:
    rel = "src/com/android/launcher3/Workspace.java"
    marker = "XAULINXS_WORKSPACE_REAPPLY_COVERFLOW_HOOK"

    old = '''    private void updatePageScrollValues() {
        int screenCenter = getScrollX() + getMeasuredWidth() / 2;
        for (int i = 0; i < getChildCount(); i++) {
            CellLayout child = (CellLayout) getChildAt(i);
            if (child != null) {
                float scrollProgress = getScrollProgress(screenCenter, child, i);
                child.setScrollProgress(scrollProgress);
                // XAULINXS_CASCADE_HOOK_COVERFLOW_WORKSPACE
                CinematicCoverFlowEffect.applyToPage(child, scrollProgress);
            }
        }
    }'''

    new = '''    private void updatePageScrollValues() {
        int screenCenter = getScrollX() + getMeasuredWidth() / 2;
        for (int i = 0; i < getChildCount(); i++) {
            CellLayout child = (CellLayout) getChildAt(i);
            if (child != null) {
                float scrollProgress = getScrollProgress(screenCenter, child, i);
                child.setScrollProgress(scrollProgress);
                // XAULINXS_CASCADE_HOOK_COVERFLOW_WORKSPACE
                CinematicCoverFlowEffect.applyToPage(child, scrollProgress);
            }
        }
    }

    /**
     * XaulinXs Customizations — não faz parte do AOSP original.
     * Wrapper público de updatePageScrollValues(), para permitir que
     * GyroTiltProvider force a reaplicação imediata do coverflow (rotação
     * das páginas) fora de um evento de scroll real — necessário porque
     * updatePageScrollValues() só é chamado nativamente a partir de
     * onScrollChanged()/bindAndInitFirstWorkspaceScreen(), então sem isso
     * desligar o interruptor de giroscópio só "sumiria" visualmente na
     * próxima vez que o usuário arrastasse entre telas.
     */
    public void xaulinXsReapplyCoverFlow() {
        updatePageScrollValues();
    }
    // XAULINXS_WORKSPACE_REAPPLY_COVERFLOW_HOOK'''

    patch_file(rel, marker, old, new, "Workspace: hook público para reaplicar coverflow")


# ---------------------------------------------------------------------------
# Fix 2: transparência do menu de apps não tinha efeito
# ---------------------------------------------------------------------------

def fix_allapps_transparency_real_layer() -> None:
    rel = "modules/customizations/src/com/xaulinxs/customizations/theme/WallpaperScrimHelper.kt"
    marker = "fun applyAllAppsTransparency"

    old = "object WallpaperScrimHelper {"
    new = '''/**
 * XaulinXs Customizations: aplica o alpha da transparência do menu de apps
 * (sem blur) sobre uma cor de fundo já resolvida. Função top-level (não
 * dentro do object WallpaperScrimHelper) para ser chamada a partir do Java
 * como WallpaperScrimHelperKt.applyAllAppsTransparency(...) — é o ponto
 * real onde o retângulo de fundo do drawer é pintado por cima de tudo
 * (inclusive por cima do blur/WallpaperGradientView), então é aqui que o
 * slider precisa agir de fato, não em getWorkspaceScrimColor() (que
 * também foi ajustado, mas fica embaixo dessa camada e nunca aparece
 * sozinho).
 *
 * Só reduz o alpha quando a nova transparência está ativada; caso
 * contrário devolve a cor original intacta (comportamento AOSP normal).
 */
fun applyAllAppsTransparency(context: Context, baseColor: Int): Int {
    val prefs = LauncherPrefs.get(context)
    if (!prefs.get(ALLAPPS_TRANSPARENCY_ENABLED)) return baseColor
    val percent = prefs.get(ALLAPPS_TRANSPARENCY_PERCENT)
        .coerceIn(ALLAPPS_TRANSPARENCY_MIN_PERCENT, ALLAPPS_TRANSPARENCY_MAX_PERCENT)
    val baseAlpha = android.graphics.Color.alpha(baseColor)
    val alpha = (baseAlpha * percent / 100).coerceIn(0, 255)
    return ColorUtils.setAlphaComponent(baseColor, alpha)
}

object WallpaperScrimHelper {'''

    patch_file(rel, marker, old, new,
               "WallpaperScrimHelper: função applyAllAppsTransparency (camada real)")


def fix_allapps_container_background() -> None:
    rel = "src/com/android/launcher3/allapps/ActivityAllAppsContainerView.java"
    marker = "XAULINXS_ALLAPPS_TRANSPARENCY_REAL_HOOK"

    old = '''    int getBackgroundColor() {
        return isBackgroundBlurEnabled()
                ? mBottomSheetBackgroundColorOverBlur
                : mBottomSheetBackgroundColorBlurFallback;
    }'''

    new = '''    int getBackgroundColor() {
        if (isBackgroundBlurEnabled()) {
            return mBottomSheetBackgroundColorOverBlur;
        }
        // XaulinXs Customizations: quando o blur do menu de apps está
        // desligado, este era o retângulo opaco (mBottomSheetBackgroundColorBlurFallback)
        // pintado por cima de TUDO em drawOnScrimWithScaleAndBottomOffset —
        // inclusive por cima da WallpaperGradientView e de qualquer alpha
        // vindo de AllAppsState.getWorkspaceScrimColor()/WallpaperScrimHelper,
        // por isso a transparência não tinha efeito nenhum visualmente
        // mesmo com o valor correto sendo calculado em outro lugar. Aqui é
        // o ponto real que precisa respeitar o slider.
        return com.xaulinxs.customizations.theme.WallpaperScrimHelperKt.applyAllAppsTransparency(
                getContext(), mBottomSheetBackgroundColorBlurFallback);
    }
    // XAULINXS_ALLAPPS_TRANSPARENCY_REAL_HOOK'''

    patch_file(rel, marker, old, new,
               "ActivityAllAppsContainerView: getBackgroundColor() respeita a transparência")


def fix_redraw_helper_invalidate_scrim() -> None:
    rel = "modules/customizations/src/com/xaulinxs/customizations/theme/XaulinXsAllAppsTransparencyRedraw.kt"
    marker = "launcher.scrimView?.invalidate()"

    old = '''object XaulinXsAllAppsTransparencyRedraw {
    @JvmStatic
    fun requestRedraw(context: Context) {
        try {
            // reapplyState() força o StateManager a rodar de novo o setScrim()
            // do estado atual, que é o que efetivamente chama
            // getWorkspaceScrimColor(mLauncher) e empurra a cor recalculada
            // pro ScrimView — invalidate() sozinho não bastaria, pois só
            // redesenha com a cor JÁ setada, sem recalculá-la.
            Launcher.getLauncher(context)?.stateManager?.reapplyState()
        } catch (_: Exception) {'''

    new = '''object XaulinXsAllAppsTransparencyRedraw {
    @JvmStatic
    fun requestRedraw(context: Context) {
        try {
            val launcher = Launcher.getLauncher(context) ?: return
            // reapplyState() força o StateManager a rodar de novo o setScrim()
            // do estado atual, que é o que efetivamente chama
            // getWorkspaceScrimColor(mLauncher) e empurra a cor recalculada
            // pro ScrimView.
            launcher.stateManager.reapplyState()
            // getBackgroundColor() de ActivityAllAppsContainerView (a camada
            // real que aplica esta transparência, ver
            // applyAllAppsTransparency() em WallpaperScrimHelper.kt) só é
            // repintada dentro de ScrimView.onDraw() via
            // drawOnScrimWithScaleAndBottomOffset — força o invalidate()
            // explicitamente para garantir o redesenho na hora.
            launcher.scrimView?.invalidate()
        } catch (_: Exception) {'''

    patch_file(rel, marker, old, new,
               "XaulinXsAllAppsTransparencyRedraw: invalidate() explícito no ScrimView")


def main() -> None:
    print(f"Aplicando correções em: {ROOT}\\n")

    if not (ROOT / "src" / "com" / "android" / "launcher3").exists():
        fail(
            "Não parece a raiz do checkout do XaulinXsLauncher3 "
            "(src/com/android/launcher3 não encontrado)."
        )

    gyro_setting_file = ROOT / "src/com/xaulinxs/customizations/cinematic/XaulinXsGyroTiltSetting.kt"
    if not gyro_setting_file.exists():
        fail(
            "Não encontrei XaulinXsGyroTiltSetting.kt — parece que "
            "apply_gyro_toggle_and_allapps_transparency.py ainda não foi "
            "rodado neste checkout. Rode ele primeiro."
        )

    fix_gyro_toggle()
    fix_workspace_reapply_hook()
    print()
    fix_allapps_transparency_real_layer()
    fix_allapps_container_background()
    fix_redraw_helper_invalidate_scrim()

    print()
    print("Correções aplicadas:")
    print("  1) Giroscópio: desligar o interruptor agora para o efeito na hora")
    print("     (cancela a SpringAnimation em voo + força redesenho imediato)")
    print("  2) Transparência do menu de apps: agora atua na camada real")
    print("     (ActivityAllAppsContainerView, que antes ficava opaca por cima")
    print("     de tudo independente do slider)")
    print()
    print("Build: ./gradlew assembleNoQuickstepDebug")


if __name__ == "__main__":
    main()
