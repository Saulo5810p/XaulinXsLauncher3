#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XaulinXs Customizations — Feature 7/N (NOVA PRIORIDADE MÁXIMA, acima de
adicionar/remover widget e pastas): scroll 3D cinematográfico verdadeiro
(coverflow em perspectiva) + tilt por giroscópio, portado de
CoverFlow3DCarousel.kt do RetroPlayer. COMBINA com o motion blur simples
já existente (feature 2) — não substitui.

Duas partes entregues neste script:

  1) GyroTiltProvider.kt (novo): porta de SensorTiltUtil.kt do RetroPlayer
     (TYPE_ACCELEROMETER, normalizado a ±12°, SENSOR_DELAY_UI) para View
     System puro. Singleton com lifecycle por View via
     View.OnAttachStateChangeListener (registra o sensor quando a
     primeira view interessada é anexada, desregistra quando a última se
     desanexa — evita vazar sensor/bateria). Suaviza com SpringAnimation
     (androidx.dynamicanimation, já dependência do projeto).

  2) CinematicCoverFlowEffect.kt (novo): rotação Y verdadeira em
     perspectiva por PÁGINA no Workspace, mesma matemática do
     CoverFlow3DCarousel original (rotationY = pageOffset * -58°,
     clamp ±75°, scale/alpha por distância do centro, cameraDistance para
     perspectiva real) + tilt do giroscópio somado. Reaproveita
     getScrollProgress(screenCenter, view, page) — método NATIVO do
     PagedView já usado por Workspace.updatePageScrollValues() para
     efeitos de fade — como equivalente exato ao pageOffset do
     HorizontalPager do player, sem duplicar cálculo de posição.

  Hook único: Workspace.updatePageScrollValues(), já chamado
  nativamente em onScrollChanged (cobre arrasto manual E fling
  automaticamente, sem precisar de hooks adicionais em PagedView.java).

  AllApps (rotação por ÍCONE individual, não por página) fica para um
  script de continuação (feature_cinematic_7b), por ser uma superfície
  com arquitetura de scroll diferente (RecyclerView vertical vs PagedView
  horizontal) — mantém este script focado e testável isoladamente.

Todas as edições são ADITIVAS: nenhuma lógica de scroll/posicionamento
real é alterada, só efeito visual por cima via propriedades de
transformação da View (rotationY, scaleX/Y, alpha, cameraDistance) — que
já são usadas passivamente pelo próprio AOSP nesse mesmo método para
fade. Script idempotente — pode rodar várias vezes sem duplicar nada.

Uso:
    python3 feature_cinematic_7_coverflow_3d_workspace.py /caminho/do/repo
    (ou rode de dentro da raiz do repo sem argumento)
"""

import os
import sys

MARKER_GYRO_FILE = "// XAULINXS_GYRO_PROVIDER_FILE"
MARKER_COVERFLOW_FILE = "// XAULINXS_COVERFLOW_EFFECT_FILE"
MARKER_WORKSPACE_HOOK = "// XAULINXS_CASCADE_HOOK_COVERFLOW_WORKSPACE"

GYRO_FILE_PATH = "src/com/xaulinxs/customizations/cinematic/GyroTiltProvider.kt"
COVERFLOW_FILE_PATH = "src/com/xaulinxs/customizations/cinematic/CinematicCoverFlowEffect.kt"

GYRO_FILE_CONTENT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Tilt de inclinação por giroscópio/acelerômetro, portado de
 * SensorTiltUtil.kt do RetroPlayer (rememberDeviceTilt). Lá é Composable
 * com DisposableEffect; aqui é um singleton View System com lifecycle
 * por View.OnAttachStateChangeListener — múltiplas views (Workspace,
 * AllApps) podem se inscrever ao mesmo tempo, o sensor só é registrado
 * enquanto pelo menos uma está anexada à janela, e desregistrado quando
 * a última se desanexa (evita vazar bateria/sensor).
 *
 * Mesma calibração do player: TYPE_ACCELEROMETER, normalizado para
 * ±12°, SENSOR_DELAY_UI. Suavização via SpringAnimation (em vez de
 * animateFloatAsState do Compose) com stiffness equivalente.
 */
package com.xaulinxs.customizations.cinematic

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.view.View
import androidx.dynamicanimation.animation.FloatValueHolder
import androidx.dynamicanimation.animation.SpringAnimation
import androidx.dynamicanimation.animation.SpringForce

object GyroTiltProvider {

    private const val MAX_TILT_DEGREES = 12f
    private const val GRAVITY_MS2 = 9.81f

    @Volatile
    var tiltX: Float = 0f
        private set

    @Volatile
    var tiltY: Float = 0f
        private set

    private var sensorManager: SensorManager? = null
    private var accelerometer: Sensor? = null
    private var listenerRegistered = false
    private val subscribedViews = java.util.Collections.newSetFromMap(
        java.util.WeakHashMap<View, Boolean>()
    )

    private var rawTiltX = 0f
    private var rawTiltY = 0f

    private val springX = SpringAnimation(FloatValueHolder(0f)).apply {
        setSpring(SpringForce(0f).apply { stiffness = 200f; dampingRatio = 0.9f })
        addUpdateListener { _, value, _ -> tiltX = value }
    }
    private val springY = SpringAnimation(FloatValueHolder(0f)).apply {
        setSpring(SpringForce(0f).apply { stiffness = 200f; dampingRatio = 0.9f })
        addUpdateListener { _, value, _ -> tiltY = value }
    }

    private val sensorListener = object : SensorEventListener {
        override fun onSensorChanged(event: SensorEvent?) {
            if (event?.sensor?.type != Sensor.TYPE_ACCELEROMETER) return
            val x = event.values[0]
            val y = event.values[1]
            rawTiltX = (x / GRAVITY_MS2 * MAX_TILT_DEGREES).coerceIn(-MAX_TILT_DEGREES, MAX_TILT_DEGREES)
            rawTiltY = (y / GRAVITY_MS2 * MAX_TILT_DEGREES).coerceIn(-MAX_TILT_DEGREES, MAX_TILT_DEGREES)
            springX.spring.finalPosition = rawTiltX
            springY.spring.finalPosition = rawTiltY
            springX.start()
            springY.start()
        }

        override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
    }

    private val attachListener = object : View.OnAttachStateChangeListener {
        override fun onViewAttachedToWindow(v: View) {
            subscribedViews.add(v)
            ensureRegistered(v.context)
        }

        override fun onViewDetachedFromWindow(v: View) {
            subscribedViews.remove(v)
            if (subscribedViews.isEmpty()) unregister()
        }
    }

    /**
     * Inscreve uma View para manter o sensor de giroscópio ativo enquanto
     * ela estiver anexada à janela. Chamar uma vez, tipicamente em
     * onAttachedToWindow/init da View interessada (Workspace, AllApps).
     * Seguro chamar múltiplas vezes para a mesma View.
     */
    @JvmStatic
    fun subscribe(view: View) {
        view.removeOnAttachStateChangeListener(attachListener)
        view.addOnAttachStateChangeListener(attachListener)
        if (view.isAttachedToWindow) {
            subscribedViews.add(view)
            ensureRegistered(view.context)
        }
    }

    private fun ensureRegistered(context: Context) {
        if (listenerRegistered) return
        val mgr = context.applicationContext
            .getSystemService(Context.SENSOR_SERVICE) as? SensorManager ?: return
        val sensor = mgr.getDefaultSensor(Sensor.TYPE_ACCELEROMETER) ?: return
        sensorManager = mgr
        accelerometer = sensor
        mgr.registerListener(sensorListener, sensor, SensorManager.SENSOR_DELAY_UI)
        listenerRegistered = true
    }

    private fun unregister() {
        sensorManager?.unregisterListener(sensorListener)
        listenerRegistered = false
        tiltX = 0f
        tiltY = 0f
        rawTiltX = 0f
        rawTiltY = 0f
    }
}
''' + f"\n{MARKER_GYRO_FILE}\n"

COVERFLOW_FILE_CONTENT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Rotação 3D verdadeira em perspectiva (coverflow) por PÁGINA no
 * Workspace, portada de CoverFlow3DCarousel.kt do RetroPlayer. COMBINA
 * com o motion blur de velocidade já existente (CinematicScrollVelocityEffect,
 * feature 2) — os dois efeitos rodam ao mesmo tempo, um na PagedView
 * inteira (blur) e este por página filha (rotação/escala/perspectiva).
 *
 * Matemática idêntica ao player, com pageOffset calculado via
 * getScrollProgress() nativo do PagedView (já usado pelo próprio AOSP em
 * Workspace.updatePageScrollValues() para efeitos de fade) em vez de
 * PagerState.currentPageOffsetFraction do Compose:
 *
 *   rotationY = (pageOffset * -58°).coerceIn(-75°, 75°)  + tilt giroscópio
 *   scale     = (1.18 - |pageOffset| * 0.28).coerceIn(0.60, 1.25)
 *   alpha     = (1 - |pageOffset| * 0.32).coerceIn(0.35, 1)
 *   cameraDistance = valor alto para perspectiva suave (mesmo princípio
 *                    do cameraDistance = 18.dp * density do Compose)
 */
package com.xaulinxs.customizations.cinematic

import android.view.View
import kotlin.math.abs

object CinematicCoverFlowEffect {

    private const val ROTATION_MULTIPLIER = -58f
    private const val ROTATION_MAX = 75f
    private const val SCALE_BASE = 1.18f
    private const val SCALE_FALLOFF = 0.28f
    private const val SCALE_MIN = 0.60f
    private const val SCALE_MAX = 1.25f
    private const val ALPHA_FALLOFF = 0.32f
    private const val ALPHA_MIN = 0.35f
    // Mesmo princípio do cameraDistance = 18.dp * density do Compose:
    // quanto MAIOR o valor, mais SUTIL a perspectiva (é um divisor óptico
    // no Camera do android.graphics, não multiplicador). View.setCameraDistance
    // espera pixels já multiplicados pela densidade da tela.
    private const val CAMERA_DISTANCE_DP = 1800f

    /**
     * Aplica a rotação 3D em perspectiva a UMA página (CellLayout do
     * Workspace), dado seu scrollProgress já calculado nativamente pelo
     * PagedView (getScrollProgress) — equivalente exato ao pageOffset do
     * player. Chamar para cada página filha, tipicamente dentro de
     * Workspace.updatePageScrollValues().
     */
    @JvmStatic
    fun applyToPage(page: View, scrollProgress: Float) {
        val pageOffset = scrollProgress.coerceIn(-1.4f, 1.4f)
        val absOffset = abs(pageOffset)

        val rotationY = (pageOffset * ROTATION_MULTIPLIER)
            .coerceIn(-ROTATION_MAX, ROTATION_MAX) + (GyroTiltProvider.tiltX * 0.55f)
        val scale = (SCALE_BASE - (absOffset * SCALE_FALLOFF)).coerceIn(SCALE_MIN, SCALE_MAX)
        val alpha = (1f - (absOffset * ALPHA_FALLOFF)).coerceIn(ALPHA_MIN, 1f)

        page.cameraDistance = CAMERA_DISTANCE_DP * page.resources.displayMetrics.density
        page.rotationY = rotationY
        page.rotationX = GyroTiltProvider.tiltY * 0.35f
        page.scaleX = scale
        page.scaleY = scale
        page.alpha = alpha
    }

    /**
     * Reseta uma página para o estado neutro (sem rotação/escala/perspectiva).
     * Chamar ao desligar o efeito ou remover a página, para não deixar
     * transformações "presas" numa view que será reciclada/reposicionada.
     */
    @JvmStatic
    fun resetPage(page: View) {
        page.rotationY = 0f
        page.rotationX = 0f
        page.scaleX = 1f
        page.scaleY = 1f
        page.alpha = 1f
        page.cameraDistance = 0f
    }
}
''' + f"\n{MARKER_COVERFLOW_FILE}\n"

WORKSPACE_REL_PATH = "src/com/android/launcher3/Workspace.java"


def find_repo_root(start):
    candidates = [start] + ([os.path.join(start, d) for d in os.listdir(start)] if os.path.isdir(start) else [])
    for c in candidates:
        if os.path.isfile(os.path.join(c, WORKSPACE_REL_PATH)):
            return c
    return None


def write_file_if_needed(repo_root, rel_path, content, marker, label):
    path = os.path.join(repo_root, rel_path)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read()
        if marker in existing:
            print(f"[=] {rel_path} já existe e está atualizado — pulando.")
            return
        print(f"[~] {rel_path} existe mas parece desatualizado — sobrescrevendo.")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] Criado {rel_path}")


def patch_workspace(repo_root):
    path = os.path.join(repo_root, WORKSPACE_REL_PATH)
    if not os.path.isfile(path):
        print(f"[!] ERRO: {path} não encontrado. Estrutura do repo mudou? Abortando este hook.")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if MARKER_WORKSPACE_HOOK in content:
        print("[=] Workspace.java já tem o hook do coverflow 3D — pulando.")
        return True

    # Import (arquivo .java, mesma convenção usada nos hooks anteriores em Workspace.java)
    import_anchor = "import com.android.launcher3.dragndrop.DragController;\n"
    new_import = "import com.xaulinxs.customizations.cinematic.CinematicCoverFlowEffect;\n"
    if import_anchor not in content:
        print("[!] ERRO: âncora de import não encontrada em Workspace.java — abortando este hook.")
        return False
    if new_import not in content:
        content = content.replace(import_anchor, import_anchor + new_import, 1)

    old_method = (
        "    private void updatePageScrollValues() {\n"
        "        int screenCenter = getScrollX() + getMeasuredWidth() / 2;\n"
        "        for (int i = 0; i < getChildCount(); i++) {\n"
        "            CellLayout child = (CellLayout) getChildAt(i);\n"
        "            if (child != null) {\n"
        "                float scrollProgress = getScrollProgress(screenCenter, child, i);\n"
        "                child.setScrollProgress(scrollProgress);\n"
        "            }\n"
        "        }\n"
        "    }\n"
    )
    new_method = (
        "    private void updatePageScrollValues() {\n"
        "        int screenCenter = getScrollX() + getMeasuredWidth() / 2;\n"
        "        for (int i = 0; i < getChildCount(); i++) {\n"
        "            CellLayout child = (CellLayout) getChildAt(i);\n"
        "            if (child != null) {\n"
        "                float scrollProgress = getScrollProgress(screenCenter, child, i);\n"
        "                child.setScrollProgress(scrollProgress);\n"
        f"                {MARKER_WORKSPACE_HOOK}\n"
        "                CinematicCoverFlowEffect.applyToPage(child, scrollProgress);\n"
        "            }\n"
        "        }\n"
        "    }\n"
    )
    if old_method not in content:
        print("[!] ERRO: corpo de updatePageScrollValues() não encontrado (formatação mudou?) — abortando este hook.")
        return False
    content = content.replace(old_method, new_method, 1)

    # Inscreve o Workspace no GyroTiltProvider assim que a janela anexa
    # (mesmo ponto já usado por mWallpaperOffset.setWindowToken, linha
    # imediatamente anterior no onAttachedToWindow original).
    old_attach = (
        "    protected void onAttachedToWindow() {\n"
        "        super.onAttachedToWindow();\n"
        "        mWallpaperOffset.setWindowToken(getWindowToken());\n"
    )
    new_attach = (
        "    protected void onAttachedToWindow() {\n"
        "        super.onAttachedToWindow();\n"
        "        mWallpaperOffset.setWindowToken(getWindowToken());\n"
        "        com.xaulinxs.customizations.cinematic.GyroTiltProvider.subscribe(this);\n"
    )
    if old_attach not in content:
        print("[!] ERRO: corpo de onAttachedToWindow() não encontrado — abortando este hook.")
        return False
    content = content.replace(old_attach, new_attach, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] Workspace.java: coverflow 3D por página + inscrição no giroscópio adicionados")
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
            "    python3 feature_cinematic_7_coverflow_3d_workspace.py /caminho/do/repo"
        )
        sys.exit(1)

    print(f"[i] Repo detectado em: {repo_root}\n")

    write_file_if_needed(repo_root, GYRO_FILE_PATH, GYRO_FILE_CONTENT, MARKER_GYRO_FILE, "giroscópio")
    write_file_if_needed(repo_root, COVERFLOW_FILE_PATH, COVERFLOW_FILE_CONTENT, MARKER_COVERFLOW_FILE, "coverflow")
    ok = patch_workspace(repo_root)

    print("")
    if ok:
        print("[OK] Feature 7/N (parte 1: Workspace) aplicada com sucesso. Rode:")
        print("     ./gradlew :quickstep:assembleDebug")
        print("     (ou o módulo correspondente que você usa para compilar o Launcher3)")
        print("")
        print("     Parte 2 (rotação 3D por ícone no AllApps) vem em script separado")
        print("     depois de você confirmar que esta parte compilou e está funcionando.")
    else:
        print("[FALHOU] O hook não foi aplicado — veja os erros [!] acima.")
        print("         Confira com 'git diff' antes de compilar.")
        sys.exit(2)


if __name__ == "__main__":
    main()
