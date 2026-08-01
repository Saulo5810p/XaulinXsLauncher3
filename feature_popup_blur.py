#!/usr/bin/env python3
"""
Feature: Balões de contexto (long-press) com blur atrás do popup.

O que este script faz:
1. Cria modules/customizations/.../blur/XaulinXsPopupBlurHelper.kt (arquivo novo,
   nosso pacote) — ponte entre o popup AOSP e o XaulinXsDepthController.
2. Edita XaulinXsDepthController.kt (nosso arquivo) para suportar um segundo
   "motivo" de blur (popup aberto) além do progresso do App Drawer, sem que um
   desative o outro.
3. Edita cirurgicamente ArrowPopup.java (AOSP) — 2 linhas + comentário cada,
   em show() e closeComplete() — para acionar/desligar o blur do popup.
4. Edita cirurgicamente Launcher.java (AOSP) — adiciona 1 getter público para
   o XaulinXsDepthController (hoje é campo privado).

Idempotente: pode rodar quantas vezes quiser, cada etapa checa se já foi
aplicada antes de mexer.

Rode a partir da RAIZ do repositório:
    python3 feature_popup_blur.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

DEPTH_CONTROLLER = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/blur/XaulinXsDepthController.kt"
POPUP_HELPER = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/blur/XaulinXsPopupBlurHelper.kt"
ARROW_POPUP = REPO_ROOT / "src/com/android/launcher3/popup/ArrowPopup.java"
LAUNCHER = REPO_ROOT / "src/com/android/launcher3/Launcher.java"

MARKER = "XaulinXsPopupBlurHelper"


def fail(msg: str):
    print(f"[ERRO] {msg}")
    sys.exit(1)


def require_file(path: Path):
    if not path.exists():
        fail(
            f"Arquivo não encontrado: {path}\n"
            "Confirme que está rodando este script a partir da raiz do repositório "
            "e que o repo está no estado esperado pelo HANDOFF."
        )


def apply_replace(path: Path, old: str, new: str, step_name: str) -> bool:
    """Substitui old->new em path. Retorna True se aplicou, False se old não
    foi encontrado (mas MARKER já presente, ou seja, provavelmente já aplicado)."""
    text = path.read_text(encoding="utf-8")
    if old not in text:
        fail(
            f"[{step_name}] Âncora esperada não encontrada em {path}.\n"
            "O arquivo pode ter mudado desde o HANDOFF (você mencionou que reclona "
            "com frequência). Cole o conteúdo atual do arquivo para eu regenerar o patch."
        )
    count = text.count(old)
    if count != 1:
        fail(f"[{step_name}] Âncora encontrada {count} vezes em {path}, esperava 1. Abortando por segurança.")
    text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print(f"[OK] {step_name} aplicado em {path.relative_to(REPO_ROOT)}")
    return True


def step_create_popup_helper():
    require_file(POPUP_HELPER.parent)
    if POPUP_HELPER.exists() and MARKER in POPUP_HELPER.read_text(encoding="utf-8"):
        print(f"[SKIP] {POPUP_HELPER.relative_to(REPO_ROOT)} já existe, nada a fazer.")
        return
    content = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Ponte entre qualquer ArrowPopup (balão de long-press: menu de contexto de
 * ícone, options popup, etc.) e o XaulinXsDepthController já usado pelo App
 * Drawer. Enquanto o popup está visível, aplicamos o mesmo blur real
 * (RenderEffect) em workspace + hotseat (os depthBlurTargets do AOSP) —
 * ou seja, borramos o que fica ATRÁS do popup, não o popup em si.
 *
 * Chamado a partir de ArrowPopup.java (show() / closeComplete()) via edição
 * cirúrgica — ver comentários "XaulinXs Customizations" lá.
 */
package com.xaulinxs.customizations.blur

import com.android.launcher3.Launcher
import com.android.launcher3.views.ActivityContext

object XaulinXsPopupBlurHelper {

    fun onPopupShown(activityContext: ActivityContext?) {
        (activityContext as? Launcher)?.xaulinXsDepthController?.setPopupBlurActive(true)
    }

    fun onPopupClosed(activityContext: ActivityContext?) {
        (activityContext as? Launcher)?.xaulinXsDepthController?.setPopupBlurActive(false)
    }
}
'''
    POPUP_HELPER.write_text(content, encoding="utf-8")
    print(f"[OK] Criado {POPUP_HELPER.relative_to(REPO_ROOT)}")


def step_patch_depth_controller():
    require_file(DEPTH_CONTROLLER)
    text = DEPTH_CONTROLLER.read_text(encoding="utf-8")
    if "setPopupBlurActive" in text:
        print(f"[SKIP] {DEPTH_CONTROLLER.relative_to(REPO_ROOT)} já tem setPopupBlurActive.")
        return

    old_field = "    private var currentDepth = 0f\n"
    new_field = (
        "    private var currentDepth = 0f\n"
        "    // XaulinXs Customizations: motivo extra de blur, independente do progresso\n"
        "    // do App Drawer — ativado enquanto um balão de contexto (long-press) está aberto.\n"
        "    private var popupBlurActive = false\n"
        "    private var appliedDepth = 0f\n"
    )
    apply_replace(DEPTH_CONTROLLER, old_field, new_field, "DepthController: campos de estado")

    old_set_depth = (
        "    fun setDepth(depth: Float) {\n"
        "        val clamped = depth.coerceIn(0f, 1f)\n"
        "        val target = if (isEnabled) clamped else 0f\n"
        "        XaulinXsWindowBlurStateHolder.setBlurEnabled(\n"
        "            isEnabled && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S\n"
        "        )\n"
        "        if (target == currentDepth) return\n"
        "        currentDepth = target\n"
        "        applyBlur(target)\n"
        "    }\n"
    )
    new_set_depth = (
        "    fun setDepth(depth: Float) {\n"
        "        val clamped = depth.coerceIn(0f, 1f)\n"
        "        currentDepth = if (isEnabled) clamped else 0f\n"
        "        XaulinXsWindowBlurStateHolder.setBlurEnabled(\n"
        "            isEnabled && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S\n"
        "        )\n"
        "        applyEffectiveBlur()\n"
        "    }\n"
        "\n"
        "    // XaulinXs Customizations: liga/desliga o blur por causa de um balão de\n"
        "    // contexto aberto. Não conflita com o progresso do App Drawer: o efeito\n"
        "    // aplicado é sempre o maior entre os dois motivos (ver applyEffectiveBlur).\n"
        "    fun setPopupBlurActive(active: Boolean) {\n"
        "        if (popupBlurActive == active) return\n"
        "        popupBlurActive = active\n"
        "        applyEffectiveBlur()\n"
        "    }\n"
        "\n"
        "    private fun applyEffectiveBlur() {\n"
        "        val target = if (!isEnabled) 0f else maxOf(currentDepth, if (popupBlurActive) 1f else 0f)\n"
        "        if (target == appliedDepth) return\n"
        "        appliedDepth = target\n"
        "        applyBlur(target)\n"
        "    }\n"
    )
    apply_replace(DEPTH_CONTROLLER, old_set_depth, new_set_depth, "DepthController: setDepth + setPopupBlurActive")


def step_patch_launcher_getter():
    require_file(LAUNCHER)
    text = LAUNCHER.read_text(encoding="utf-8")
    if "getXaulinXsDepthController" in text:
        print(f"[SKIP] {LAUNCHER.relative_to(REPO_ROOT)} já tem getXaulinXsDepthController().")
        return
    old = (
        "    /** @return list of View targets to be blurred based on changes to depth. */\n"
        "    @NonNull\n"
        "    public List<View> getDepthBlurTargets() {\n"
        "        return mDepthBlurTargets == null ? Collections.emptyList() : mDepthBlurTargets;\n"
        "    }\n"
    )
    new = old + (
        "\n"
        "    // XaulinXs Customizations: getter público para o XaulinXsPopupBlurHelper\n"
        "    // acionar o blur ao abrir/fechar um balão de contexto (long-press).\n"
        "    public com.xaulinxs.customizations.blur.XaulinXsDepthController getXaulinXsDepthController() {\n"
        "        return mXaulinXsDepthController;\n"
        "    }\n"
    )
    apply_replace(LAUNCHER, old, new, "Launcher.java: getter do DepthController")


def step_patch_arrow_popup():
    require_file(ARROW_POPUP)
    text = ARROW_POPUP.read_text(encoding="utf-8")
    if MARKER in text:
        print(f"[SKIP] {ARROW_POPUP.relative_to(REPO_ROOT)} já tem o hook do {MARKER}.")
        return

    old_show = (
        "    public void show() {\n"
        "        setupForDisplay();\n"
        "        assignMarginsAndBackgrounds(this);\n"
        "        if (shouldAddArrow()) {\n"
        "            addArrow();\n"
        "        }\n"
        "        animateOpen();\n"
        "    }\n"
    )
    new_show = (
        "    public void show() {\n"
        "        setupForDisplay();\n"
        "        assignMarginsAndBackgrounds(this);\n"
        "        if (shouldAddArrow()) {\n"
        "            addArrow();\n"
        "        }\n"
        "        // XaulinXs Customizations: aciona o blur real atrás do popup ao abrir\n"
        "        com.xaulinxs.customizations.blur.XaulinXsPopupBlurHelper.onPopupShown(mActivityContext);\n"
        "        animateOpen();\n"
        "    }\n"
    )
    apply_replace(ARROW_POPUP, old_show, new_show, "ArrowPopup.java: hook em show()")

    old_close = (
        "    protected void closeComplete() {\n"
        "        if (mOpenCloseAnimator != null) {\n"
        "            mOpenCloseAnimator.cancel();\n"
        "            mOpenCloseAnimator = null;\n"
        "        }\n"
        "        mIsOpen = false;\n"
        "        mDeferContainerRemoval = false;\n"
        "        getPopupContainer().removeView(this);\n"
        "        getPopupContainer().removeView(mArrow);\n"
        "        mOnCloseCallbacks.executeAllAndClear();\n"
        "    }\n"
    )
    new_close = (
        "    protected void closeComplete() {\n"
        "        if (mOpenCloseAnimator != null) {\n"
        "            mOpenCloseAnimator.cancel();\n"
        "            mOpenCloseAnimator = null;\n"
        "        }\n"
        "        mIsOpen = false;\n"
        "        mDeferContainerRemoval = false;\n"
        "        getPopupContainer().removeView(this);\n"
        "        getPopupContainer().removeView(mArrow);\n"
        "        mOnCloseCallbacks.executeAllAndClear();\n"
        "        // XaulinXs Customizations: desativa o blur do popup ao fechar\n"
        "        com.xaulinxs.customizations.blur.XaulinXsPopupBlurHelper.onPopupClosed(mActivityContext);\n"
        "    }\n"
    )
    apply_replace(ARROW_POPUP, old_close, new_close, "ArrowPopup.java: hook em closeComplete()")


def main():
    print("== Feature: balões de contexto (long-press) com blur ==")
    step_create_popup_helper()
    step_patch_depth_controller()
    step_patch_launcher_getter()
    step_patch_arrow_popup()
    print("\nConcluído. Recompile com:")
    print("  ./gradlew assembleNoQuickstepDebug --stacktrace 2>&1 | tee build_nextNN.log")


if __name__ == "__main__":
    main()
