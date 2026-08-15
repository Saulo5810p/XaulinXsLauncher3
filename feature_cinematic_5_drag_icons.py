#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XaulinXs Customizations — Feature 5/N (item 3 da prioridade):
arrastar ícones (drag and drop).

DragView/DragController são View System puro (Java), igual ao AllApps e
ao scroll de páginas — diferente do painel de widgets (Compose). Efeito
implementado:

  1) Durante o arrasto: motion blur + aberração cromática reagindo à
     velocidade total do movimento (fórmula portada de CinematicPhysics.kt
     do RetroPlayer: blur = |velocidade| * 0.08 * multiplicador) + tilt 3D
     (rotationX/rotationY) na direção OPOSTA ao movimento, simulando
     "peso físico" — o ícone se inclina contra a direção do arrasto, como
     se tivesse inércia.

  2) Ao soltar em posição válida: bounce de impacto (overshoot de escala)
     quando a animação de voo até a célula final termina — reaproveita o
     mesmo perfil de spring usado no giro de entrada do AllApps
     (dampingRatio 0.55, overshoot 1.5x), mas aplicado só à escala, sem
     giro (o ícone já chegou na orientação correta, só "bate e assenta").

Pontos de hook (todos de 1 linha, sem reescrever lógica original):
  - DragView.move(): captura delta de posição por frame -> calcula
    velocidade -> aplica tilt+blur via CinematicDragEffect.onDragMove()
  - DragLayer.playDropAnimation(): listener adicional no Animator que
    dispara o bounce de impacto quando a animação de pouso termina —
    único ponto de convergência de todos os drops bem-sucedidos
    (Workspace, Folder, resize de widget), então cobre todos os casos
    sem duplicar lógica em cada chamador.

Todas as edições são ADITIVAS: nenhuma lógica de posicionamento,
CellLayout, ou drag-and-drop original é alterada — só efeito visual por
cima. Script idempotente — pode rodar várias vezes sem duplicar nada.

Uso:
    python3 feature_cinematic_5_drag_icons.py /caminho/do/repo
    (ou rode de dentro da raiz do repo sem argumento)
"""

import os
import sys

MARKER_DRAGVIEW_HOOK = "// XAULINXS_CASCADE_HOOK_DRAG_MOVE"
MARKER_DRAGLAYER_HOOK = "// XAULINXS_CASCADE_HOOK_DRAG_DROP_BOUNCE"
MARKER_NEW_FILE = "// XAULINXS_DRAG_EFFECT_FILE"

NEW_FILE_PATH = "src/com/xaulinxs/customizations/cinematic/CinematicDragEffect.kt"

NEW_FILE_CONTENT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Efeito cinematográfico ao arrastar ícones (DragView, View System puro).
 * Duas partes:
 *
 *  1) onDragMove(): chamado a cada frame de movimento do DragView, com o
 *     delta de posição desde o último frame (já calculado nativamente em
 *     DragView.move() como mLastTouchX - touchX / mLastTouchY - touchY).
 *     Calcula velocidade instantânea e aplica:
 *       - motion blur + aberração cromática (fórmula portada de
 *         CinematicPhysics.kt do RetroPlayer: blur = |vel| * 0.08 *
 *         multiplicador, mesma calibração usada no scroll de páginas)
 *       - tilt 3D (rotationX/rotationY) na direção OPOSTA ao movimento,
 *         simulando inércia/peso físico — não existia equivalente pronto
 *         no RetroPlayer (lá o scroll é 1D), matemática nova mas mesma
 *         filosofia de "intensidade proporcional à velocidade"
 *
 *  2) onDragDropSettled(): chamado quando a animação de voo até a célula
 *     final termina (listener em DragLayer.playDropAnimation). Aplica um
 *     bounce de overshoot na escala — mesmo spring (dampingRatio 0.55,
 *     overshoot 1.5x) do giro de entrada do AllApps, mas só na escala,
 *     sem rotação (o ícone já está na orientação final).
 */
package com.xaulinxs.customizations.cinematic

import android.os.Build
import android.view.View
import androidx.dynamicanimation.animation.FloatValueHolder
import androidx.dynamicanimation.animation.SpringAnimation
import androidx.dynamicanimation.animation.SpringForce
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.sin

object CinematicDragEffect {

    // Mesma calibração de blur/aberração cromática do scroll de páginas
    // (CinematicScrollVelocityEffect.kt) e da física original do
    // RetroPlayer (CinematicPhysics.kt: blurVal = |vel| * 0.08 * mult).
    private const val BLUR_VELOCITY_FACTOR = 0.08f
    private const val BLUR_MULTIPLIER = 2.4f
    private const val CHROMATIC_MULTIPLIER = 0.8f
    private const val VIGNETTE_MULTIPLIER = 0.4f

    // Tilt 3D máximo (graus) na direção oposta ao movimento — efeito de
    // "peso físico" sem exagerar a ponto de atrapalhar a visibilidade do
    // ícone sendo arrastado.
    private const val MAX_TILT_DEGREES = 18f
    private const val TILT_VELOCITY_DIVISOR = 40f // px/frame para atingir tilt máximo

    // Perfil de bounce ao pousar — mesmo dampingRatio/overshoot do giro de
    // entrada do AllApps (AllAppsIconEnterEffect), só que aplicado apenas
    // à escala (sem rotação, já que o ícone chega na orientação correta).
    private const val LAND_OVERSHOOT_SCALE = 1.22f

    /**
     * Chamado a cada frame de movimento do DragView, com o delta de
     * posição (em px) desde o frame anterior.
     */
    @JvmStatic
    fun onDragMove(dragView: View, deltaX: Float, deltaY: Float) {
        val speed = kotlin.math.hypot(deltaX.toDouble(), deltaY.toDouble()).toFloat()

        if (speed < 0.6f) {
            resetTilt(dragView)
            return
        }

        val normalizedSpeed = (speed * BLUR_VELOCITY_FACTOR).coerceIn(0f, 3f)

        // Tilt na direção OPOSTA ao movimento (efeito de inércia/peso):
        // se o dedo move o ícone pra direita rápido, o topo do ícone
        // "atrasa" e se inclina pra trás (rotationY negativo quando
        // deltaX > 0), como se resistisse ao puxão.
        val tiltRatio = (speed / TILT_VELOCITY_DIVISOR).coerceIn(0f, 1f)
        dragView.rotationY = -(deltaX / (abs(deltaX) + abs(deltaY) + 0.001f)) *
            MAX_TILT_DEGREES * tiltRatio
        dragView.rotationX = (deltaY / (abs(deltaX) + abs(deltaY) + 0.001f)) *
            MAX_TILT_DEGREES * tiltRatio

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val w = dragView.width.toFloat().coerceAtLeast(50f)
            val h = dragView.height.toFloat().coerceAtLeast(50f)
            val effect = CinematicShader.createCinematicEffect(
                width = w,
                height = h,
                rotationSpeed = normalizedSpeed,
                scaleFactor = 1f,
                blurIntensity = normalizedSpeed * BLUR_MULTIPLIER,
                chromaticShift = normalizedSpeed * CHROMATIC_MULTIPLIER,
                vignetteIntensity = normalizedSpeed * VIGNETTE_MULTIPLIER
            )
            dragView.setRenderEffect(effect)
        }
    }

    private fun resetTilt(dragView: View) {
        dragView.rotationX = 0f
        dragView.rotationY = 0f
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            dragView.setRenderEffect(null)
        }
    }

    /**
     * Chamado quando a animação de voo do ícone até a célula final
     * termina com sucesso (drop aceito). Dispara um bounce de overshoot
     * na escala, como "impacto ao pousar".
     */
    @JvmStatic
    fun onDragDropSettled(view: View) {
        // Reset de tilt/blur — a partir daqui só a escala anima.
        resetTilt(view)

        val baseScaleX = view.scaleX
        val baseScaleY = view.scaleY

        val holder = FloatValueHolder(0f)
        val spring = SpringAnimation(holder).apply {
            setSpring(
                SpringForce(1f).apply {
                    stiffness = SpringForce.STIFFNESS_LOW
                    dampingRatio = 0.55f
                }
            )
            setStartVelocity(0f)
            minimumVisibleChange = 0.001f
        }

        spring.addUpdateListener { _, value, _ ->
            val progress = value.coerceIn(0f, 1.4f)
            val remaining = max(0f, 1f - progress)
            val bounceScale = baseScaleX * (1f + (LAND_OVERSHOOT_SCALE - 1f) *
                sin(progress * PI.toFloat()) * remaining)
            view.scaleX = bounceScale
            view.scaleY = baseScaleY / baseScaleX.coerceAtLeast(0.001f) * bounceScale
        }
        spring.addEndListener { _, _, _, _ ->
            view.scaleX = baseScaleX
            view.scaleY = baseScaleY
        }
        spring.start()
    }
}
''' + f"\n{MARKER_NEW_FILE}\n"

DRAGVIEW_REL_PATH = "src/com/android/launcher3/dragndrop/DragView.java"
DRAGLAYER_REL_PATH = "src/com/android/launcher3/dragndrop/DragLayer.java"


def find_repo_root(start):
    candidates = [start] + ([os.path.join(start, d) for d in os.listdir(start)] if os.path.isdir(start) else [])
    for c in candidates:
        if os.path.isfile(os.path.join(c, DRAGVIEW_REL_PATH)):
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


def patch_drag_view(repo_root):
    path = os.path.join(repo_root, DRAGVIEW_REL_PATH)
    if not os.path.isfile(path):
        print(f"[!] ERRO: {path} não encontrado. Estrutura do repo mudou? Abortando este hook.")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if MARKER_DRAGVIEW_HOOK in content:
        print("[=] DragView.java já tem o hook de tilt/blur — pulando.")
        return True

    # Import da classe Kotlin (chamada estática via @JvmStatic)
    import_anchor = "import com.android.launcher3.R;\n"
    new_import = "import com.xaulinxs.customizations.cinematic.CinematicDragEffect;\n"
    if import_anchor not in content:
        print("[!] ERRO: âncora de import não encontrada em DragView.java — abortando este hook.")
        return False
    if new_import not in content:
        content = content.replace(import_anchor, import_anchor + new_import, 1)

    old_move = (
        "    public void move(int touchX, int touchY) {\n"
        "        if (touchX > 0 && touchY > 0 && mLastTouchX > 0 && mLastTouchY > 0\n"
        "                && mScaledMaskPath != null) {\n"
        "            mTranslateX.animateToPos(mLastTouchX - touchX);\n"
        "            mTranslateY.animateToPos(mLastTouchY - touchY);\n"
        "        }\n"
        "        mLastTouchX = touchX;\n"
        "        mLastTouchY = touchY;\n"
        "        applyTranslation();\n"
        "    }\n"
    )
    new_move = (
        "    public void move(int touchX, int touchY) {\n"
        "        if (touchX > 0 && touchY > 0 && mLastTouchX > 0 && mLastTouchY > 0\n"
        "                && mScaledMaskPath != null) {\n"
        "            mTranslateX.animateToPos(mLastTouchX - touchX);\n"
        "            mTranslateY.animateToPos(mLastTouchY - touchY);\n"
        "        }\n"
        f"        {MARKER_DRAGVIEW_HOOK}\n"
        "        CinematicDragEffect.onDragMove(this, mLastTouchX - touchX, mLastTouchY - touchY);\n"
        "        mLastTouchX = touchX;\n"
        "        mLastTouchY = touchY;\n"
        "        applyTranslation();\n"
        "    }\n"
    )
    if old_move not in content:
        print("[!] ERRO: corpo de DragView.move() não encontrado (formatação mudou?) — abortando este hook.")
        return False
    content = content.replace(old_move, new_move, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] DragView.java: tilt 3D + motion blur por velocidade adicionados em move()")
    return True


def patch_drag_layer(repo_root):
    path = os.path.join(repo_root, DRAGLAYER_REL_PATH)
    if not os.path.isfile(path):
        print(f"[!] ERRO: {path} não encontrado. Estrutura do repo mudou? Abortando este hook.")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if MARKER_DRAGLAYER_HOOK in content:
        print("[=] DragLayer.java já tem o hook de bounce de impacto — pulando.")
        return True

    import_anchor = "import java.util.ArrayList;\n"
    new_import = "import com.xaulinxs.customizations.cinematic.CinematicDragEffect;\n"
    if new_import not in content:
        if import_anchor not in content:
            print("[!] ERRO: âncora de import ('import java.util.ArrayList;') não encontrada em "
                  "DragLayer.java — abortando este hook.")
            return False
        content = content.replace(import_anchor, import_anchor + new_import, 1)

    old_play_drop = (
        "    public void playDropAnimation(final DragView view, Animator animator, int animationEndStyle) {\n"
        "        // Clean up the previous animations\n"
        "        if (mDropAnim != null) mDropAnim.cancel();\n"
        "\n"
        "        // Show the drop view if it was previously hidden\n"
        "        mDropView = view;\n"
        "        // Create and start the animation\n"
        "        mDropAnim = animator;\n"
        "        mDropAnim.addListener(forEndCallback(() -> mDropAnim = null));\n"
        "        if (animationEndStyle == ANIMATION_END_DISAPPEAR) {\n"
        "            mDropAnim.addListener(forEndCallback(this::clearAnimatedView));\n"
        "        }\n"
        "        mDropAnim.start();\n"
        "    }\n"
    )
    new_play_drop = (
        "    public void playDropAnimation(final DragView view, Animator animator, int animationEndStyle) {\n"
        "        // Clean up the previous animations\n"
        "        if (mDropAnim != null) mDropAnim.cancel();\n"
        "\n"
        "        // Show the drop view if it was previously hidden\n"
        "        mDropView = view;\n"
        "        // Create and start the animation\n"
        "        mDropAnim = animator;\n"
        "        mDropAnim.addListener(forEndCallback(() -> mDropAnim = null));\n"
        "        if (animationEndStyle == ANIMATION_END_DISAPPEAR) {\n"
        "            mDropAnim.addListener(forEndCallback(this::clearAnimatedView));\n"
        "        }\n"
        f"        {MARKER_DRAGLAYER_HOOK}\n"
        "        mDropAnim.addListener(forEndCallback(() -> CinematicDragEffect.onDragDropSettled(view)));\n"
        "        mDropAnim.start();\n"
        "    }\n"
    )
    if old_play_drop not in content:
        print("[!] ERRO: corpo de DragLayer.playDropAnimation() não encontrado — abortando este hook.")
        return False
    content = content.replace(old_play_drop, new_play_drop, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] DragLayer.java: bounce de impacto ao pousar adicionado em playDropAnimation()")
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
            "    python3 feature_cinematic_5_drag_icons.py /caminho/do/repo"
        )
        sys.exit(1)

    print(f"[i] Repo detectado em: {repo_root}\n")

    write_new_file(repo_root)
    ok1 = patch_drag_view(repo_root)
    ok2 = patch_drag_layer(repo_root)

    print("")
    if ok1 and ok2:
        print("[OK] Feature 5/N aplicada com sucesso. Rode:")
        print("     ./gradlew :quickstep:assembleDebug")
        print("     (ou o módulo correspondente que você usa para compilar o Launcher3)")
    else:
        print("[FALHOU] Um ou mais hooks não foram aplicados — veja os erros [!] acima.")
        print("         Confira com 'git diff' antes de compilar.")
        sys.exit(2)


if __name__ == "__main__":
    main()
