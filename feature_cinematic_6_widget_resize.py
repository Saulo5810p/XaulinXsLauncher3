#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XaulinXs Customizations — Feature 6/N (item 4 da prioridade):
arrastar/redimensionar widgets na tela.

Descoberta importante: MOVER um widget já colocado (long-press + arrastar
o corpo inteiro) reusa o mesmo DragController/DragView dos ícones — a
Feature 5 (feature_cinematic_5_drag_icons.py) já cobre esse caso
automaticamente, sem precisar de nenhum hook novo. O que resta e é
específico deste item é o efeito ao REDIMENSIONAR pelas alças/pontinhos
das bordas (AppWidgetResizeFrame.kt — View System puro, Kotlin).

Efeito implementado:
  1) Durante o arrasto de uma alça: blur + aberração cromática na MOLDURA
     do frame de resize (não no widget real — o widget continua
     redimensionando via LayoutParams normalmente, sem interferência),
     reagindo à velocidade do arrasto (mesmo esquema de
     CinematicDragEffect.onDragMove da feature 5).
  2) A alça (pontinho) especificamente sendo arrastada recebe um pulso de
     escala (glow de destaque) enquanto o gesto está ativo.
  3) Ao soltar (onTouchUp -> snapToWidget): reset do blur e da alça,
     coincidindo com a animação de snap final que já existe.

Ponto de hook único: visualizeResizeForDelta(deltaX, deltaY), já chamado
tanto durante o movimento (ACTION_MOVE) quanto no fim (ACTION_UP/CANCEL) —
mesmo padrão dos hooks anteriores (DragView.move, PagedView scroll).
Reset alinhado ao início de onTouchUp().

Todas as edições são ADITIVAS: nenhuma lógica de cálculo de resize
(LayoutParams, CellLayout, deltaXRange/deltaYRange) é alterada — só efeito
visual por cima. Script idempotente — pode rodar várias vezes sem
duplicar nada.

Uso:
    python3 feature_cinematic_6_widget_resize.py /caminho/do/repo
    (ou rode de dentro da raiz do repo sem argumento)
"""

import os
import sys

MARKER_VISUALIZE_HOOK = "// XAULINXS_CASCADE_HOOK_WIDGET_RESIZE_MOVE"
MARKER_TOUCHUP_HOOK = "// XAULINXS_CASCADE_HOOK_WIDGET_RESIZE_SETTLE"
MARKER_NEW_FILE = "// XAULINXS_RESIZE_EFFECT_FILE"

NEW_FILE_PATH = "src/com/xaulinxs/customizations/cinematic/CinematicResizeEffect.kt"

NEW_FILE_CONTENT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Efeito cinematográfico ao redimensionar widgets pelas alças/pontinhos
 * das bordas (AppWidgetResizeFrame, View System puro).
 *
 *  1) onResizeMove(): chamado a cada frame de movimento de uma alça, com
 *     o delta de posição desde o início do gesto. Aplica blur + aberração
 *     cromática na MOLDURA do frame (não no widget sendo redimensionado —
 *     esse continua sua lógica de LayoutParams intacta), reagindo à
 *     velocidade instantânea do arrasto (mesma fórmula de
 *     CinematicDragEffect: blur = |vel| * 0.08 * multiplicador) + pulso
 *     de escala na alça específica que está sendo puxada, como destaque.
 *
 *  2) onResizeSettled(): chamado ao soltar a alça, junto com o snap final
 *     do frame. Reseta blur da moldura e escala da alça.
 */
package com.xaulinxs.customizations.cinematic

import android.os.Build
import android.view.View
import kotlin.math.abs

object CinematicResizeEffect {

    // Mesma calibração de blur/aberração cromática usada no arrasto de
    // ícones (CinematicDragEffect) e no scroll de páginas — consistência
    // visual entre as superfícies de drag do launcher.
    private const val BLUR_VELOCITY_FACTOR = 0.08f
    private const val BLUR_MULTIPLIER = 2.0f
    private const val CHROMATIC_MULTIPLIER = 0.7f
    private const val VIGNETTE_MULTIPLIER = 0.3f

    // Pulso de destaque na alça ativa: escala máxima quando o arrasto
    // está em velocidade alta, suaviza de volta a 1x quando parado.
    private const val HANDLE_MAX_SCALE = 1.6f
    private const val HANDLE_VELOCITY_DIVISOR = 30f // px/frame para atingir escala máxima

    private var lastDeltaX = 0
    private var lastDeltaY = 0

    /**
     * Chamado a cada frame de movimento de uma alça de resize, com o
     * delta acumulado desde o início do gesto (deltaX/deltaY já
     * calculados nativamente em AppWidgetResizeFrame.visualizeResizeForDelta).
     * activeHandle é a View da alça (pontinho) sendo arrastada nesse
     * momento — pode ser null se nenhuma borda está ativa.
     */
    @JvmStatic
    fun onResizeMove(frame: View, deltaX: Int, deltaY: Int, activeHandle: View?) {
        val frameDeltaX = (deltaX - lastDeltaX).toFloat()
        val frameDeltaY = (deltaY - lastDeltaY).toFloat()
        lastDeltaX = deltaX
        lastDeltaY = deltaY

        val speed = kotlin.math.hypot(frameDeltaX.toDouble(), frameDeltaY.toDouble()).toFloat()

        if (speed < 0.6f) {
            resetHandle(activeHandle)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                frame.setRenderEffect(null)
            }
            return
        }

        val normalizedSpeed = (speed * BLUR_VELOCITY_FACTOR).coerceIn(0f, 3f)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val w = frame.width.toFloat().coerceAtLeast(50f)
            val h = frame.height.toFloat().coerceAtLeast(50f)
            val effect = CinematicShader.createCinematicEffect(
                width = w,
                height = h,
                rotationSpeed = normalizedSpeed,
                scaleFactor = 1f,
                blurIntensity = normalizedSpeed * BLUR_MULTIPLIER,
                chromaticShift = normalizedSpeed * CHROMATIC_MULTIPLIER,
                vignetteIntensity = normalizedSpeed * VIGNETTE_MULTIPLIER
            )
            frame.setRenderEffect(effect)
        }

        if (activeHandle != null) {
            val handleSpeedRatio = (speed / HANDLE_VELOCITY_DIVISOR).coerceIn(0f, 1f)
            val handleScale = 1f + (HANDLE_MAX_SCALE - 1f) * handleSpeedRatio
            activeHandle.scaleX = handleScale
            activeHandle.scaleY = handleScale
        }
    }

    private fun resetHandle(handle: View?) {
        handle?.scaleX = 1f
        handle?.scaleY = 1f
    }

    /**
     * Chamado ao soltar a alça (início de onTouchUp, antes do snap final
     * animado). Reseta blur da moldura e escala de todas as alças.
     */
    @JvmStatic
    fun onResizeSettled(frame: View, allHandles: List<View>) {
        lastDeltaX = 0
        lastDeltaY = 0
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            frame.setRenderEffect(null)
        }
        allHandles.forEach { resetHandle(it) }
    }
}
''' + f"\n{MARKER_NEW_FILE}\n"

RESIZE_FRAME_REL_PATH = "src/com/android/launcher3/AppWidgetResizeFrame.kt"


def find_repo_root(start):
    candidates = [start] + ([os.path.join(start, d) for d in os.listdir(start)] if os.path.isdir(start) else [])
    for c in candidates:
        if os.path.isfile(os.path.join(c, RESIZE_FRAME_REL_PATH)):
            return c
    return None


def write_new_file(repo_root):
    path = os.path.join(repo_root, NEW_FILE_PATH)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read()
        if MARKER_NEW_FILE in existing:
            print(f"[=] {NEW_FILE_PATH} já existe e está atualizado — pulando.")
            return
        print(f"[~] {NEW_FILE_PATH} existe mas parece desatualizado — sobrescrevendo.")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(NEW_FILE_CONTENT)
    print(f"[+] Criado {NEW_FILE_PATH}")


def patch_resize_frame(repo_root):
    path = os.path.join(repo_root, RESIZE_FRAME_REL_PATH)
    if not os.path.isfile(path):
        print(f"[!] ERRO: {path} não encontrado. Estrutura do repo mudou? Abortando este hook.")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if MARKER_VISUALIZE_HOOK in content:
        print("[=] AppWidgetResizeFrame.kt já tem os hooks de resize — pulando.")
        return True

    # Import (arquivo Kotlin, mesmo pacote de convenção que os outros hooks .kt)
    import_anchor = "import com.android.launcher3.widget.resize.AppWidgetResizeFrameCompose\n"
    new_import = "import com.xaulinxs.customizations.cinematic.CinematicResizeEffect\n"
    if import_anchor not in content:
        print("[!] ERRO: âncora de import não encontrada em AppWidgetResizeFrame.kt — abortando este hook.")
        return False
    if new_import not in content:
        content = content.replace(import_anchor, import_anchor + new_import, 1)

    # 1) Hook em visualizeResizeForDelta: dispara o efeito a cada frame de movimento.
    old_visualize = (
        "    private fun visualizeResizeForDelta(deltaX: Int, deltaY: Int) {\n"
        "        this.deltaX = deltaXRange.clamp(deltaX)\n"
        "        this.deltaY = deltaYRange.clamp(deltaY)\n"
        "        val lp = layoutParams as BaseDragLayer.LayoutParams\n"
    )
    new_visualize = (
        "    private fun visualizeResizeForDelta(deltaX: Int, deltaY: Int) {\n"
        "        this.deltaX = deltaXRange.clamp(deltaX)\n"
        "        this.deltaY = deltaYRange.clamp(deltaY)\n"
        f"        {MARKER_VISUALIZE_HOOK}\n"
        "        CinematicResizeEffect.onResizeMove(\n"
        "            frame = this,\n"
        "            deltaX = this.deltaX,\n"
        "            deltaY = this.deltaY,\n"
        "            activeHandle = when {\n"
        "                isLeftBorderActive -> dragHandles.left\n"
        "                isRightBorderActive -> dragHandles.right\n"
        "                isTopBorderActive -> dragHandles.top\n"
        "                isBottomBorderActive -> dragHandles.bottom\n"
        "                else -> null\n"
        "            },\n"
        "        )\n"
        "        val lp = layoutParams as BaseDragLayer.LayoutParams\n"
    )
    if old_visualize not in content:
        print("[!] ERRO: corpo de visualizeResizeForDelta() não encontrado (formatação mudou?) — abortando este hook.")
        return False
    content = content.replace(old_visualize, new_visualize, 1)

    # 2) Hook em onTouchUp: reset do efeito antes do snap final.
    old_touchup = (
        "    private fun onTouchUp() {\n"
        "        val dp = launcher.deviceProfile\n"
    )
    new_touchup = (
        "    private fun onTouchUp() {\n"
        f"        {MARKER_TOUCHUP_HOOK}\n"
        "        CinematicResizeEffect.onResizeSettled(this, dragHandles.all)\n"
        "        val dp = launcher.deviceProfile\n"
    )
    if old_touchup not in content:
        print("[!] ERRO: corpo de onTouchUp() não encontrado — abortando este hook.")
        return False
    content = content.replace(old_touchup, new_touchup, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] AppWidgetResizeFrame.kt: blur na moldura + pulso na alça ativa adicionados")
    return True


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    repo_root = find_repo_root(start)
    if repo_root is None:
        print(
            "[!] ERRO: não encontrei a estrutura esperada do XaulinXsLauncher3 "
            f"(procurado a partir de: {start}).\n"
            "    Rode este script de dentro da raiz do repo clonado, ou passe o "
            "caminho como argumento:\n"
            "    python3 feature_cinematic_6_widget_resize.py /caminho/do/repo"
        )
        sys.exit(1)

    print(f"[i] Repo detectado em: {repo_root}\n")

    write_new_file(repo_root)
    ok = patch_resize_frame(repo_root)

    print("")
    if ok:
        print("[OK] Feature 6/N aplicada com sucesso. Rode:")
        print("     ./gradlew :quickstep:assembleDebug")
        print("     (ou o módulo correspondente que você usa para compilar o Launcher3)")
    else:
        print("[FALHOU] O hook não foi aplicado — veja os erros [!] acima.")
        print("         Confira com 'git diff' antes de compilar.")
        sys.exit(2)


if __name__ == "__main__":
    main()
