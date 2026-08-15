/*
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

// XAULINXS_RESIZE_EFFECT_FILE
