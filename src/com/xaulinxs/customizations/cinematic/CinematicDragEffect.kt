/*
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

// XAULINXS_DRAG_EFFECT_FILE
