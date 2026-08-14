/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Giro 720° + motion blur + aberração cromática na entrada de cada ícone
 * do app drawer, portado do perfil NOW_PLAYING_ENTER do projeto irmão
 * RetroPlayer Compose (NowPlayingScreen.kt): rotation (eixo Z) decrescendo de
 * maxRotationDegrees até 0 conforme o progresso avança, escala com
 * overshoot senoidal, alpha fade-in, blur/aberração cromática máximos no
 * início e some ao final — mesma matemática, só trocando Animatable+spring
 * do Compose por SpringAnimation (androidx.dynamicanimation), o
 * equivalente nativo View System.
 *
 * Efeito em CASCATA: cada ícone recebe um atraso proporcional à sua
 * posição no grid, criando a sensação de "surgir" em sequência em vez de
 * todos ao mesmo tempo.
 */
package com.xaulinxs.customizations.cinematic

import android.os.Build
import android.view.View
import androidx.dynamicanimation.animation.FloatValueHolder
import androidx.dynamicanimation.animation.SpringAnimation
import androidx.dynamicanimation.animation.SpringForce
import kotlin.math.PI
import kotlin.math.max
import kotlin.math.sin

object AllAppsIconEnterEffect {

    // Mesmos valores do perfil NOW_PLAYING_ENTER (CinematicProfile.kt do
    // RetroPlayer): mass=1.5, stiffness=130, damping=6.5, rotação 720°,
    // overshoot 1.5x, blur/aberração cromática altos.
    private const val MAX_ROTATION_DEGREES = 720f
    private const val OVERSHOOT_SCALE = 1.5f
    private const val BLUR_MULTIPLIER = 3.6f
    private const val CHROMATIC_MULTIPLIER = 3.0f
    private const val VIGNETTE_MULTIPLIER = 1.0f

    // Atraso entre o início da animação de cada ícone consecutivo na
    // cascata — pequeno o bastante para não atrasar demais o último ícone
    // visível, grande o bastante para a sequência ser perceptível.
    private const val STAGGER_DELAY_MS = 18L
    private const val MAX_STAGGER_ITEMS = 30 // evita atraso enorme em grids grandes

    /**
     * Dispara a animação de entrada em cascata no ícone, com atraso
     * proporcional à posição dele no grid do app drawer.
     */
    @JvmStatic
    fun animateEnter(icon: View, positionInGrid: Int) {
        val staggerIndex = positionInGrid.coerceIn(0, MAX_STAGGER_ITEMS)
        val delayMs = staggerIndex * STAGGER_DELAY_MS

        // Estado inicial: escondido/girado, antes da spring rodar.
        icon.rotation = MAX_ROTATION_DEGREES
        icon.rotationY = 30f
        icon.scaleX = 0.05f
        icon.scaleY = 0.05f
        icon.alpha = 0f

        icon.postDelayed({ runSpring(icon) }, delayMs)
    }

    private fun runSpring(icon: View) {
        // FloatValueHolder vai de 0 a 1 (não 1000 — mSpring já trabalha
        // bem em escala 0..1, sem necessidade de normalizar depois).
        // Valores de stiffness/dampingRatio escolhidos para reproduzir o
        // "bounce" perceptível do perfil NOW_PLAYING_ENTER do RetroPlayer
        // (overshoot visível, mas sem oscilar demais) — as unidades do
        // SpringForce do Android (stiffness absoluta, dampingRatio 0..1)
        // não correspondem 1:1 às unidades do spring() do Compose, então
        // isso é uma calibração visual equivalente, não uma conversão
        // matemática direta dos mesmos números.
        val holder = FloatValueHolder(0f)
        val spring = SpringAnimation(holder).apply {
            setSpring(
                SpringForce(1f).apply {
                    stiffness = SpringForce.STIFFNESS_LOW
                    dampingRatio = 0.55f // <1 = permite overshoot visível
                }
            )
            setStartVelocity(0f)
            minimumVisibleChange = 0.001f
        }

        spring.addUpdateListener { _, value, _ ->
            applyFrame(icon, value.coerceIn(0f, 1.4f)) // permite overshoot > 1
        }
        spring.addEndListener { _, _, _, _ ->
            applyFrame(icon, 1f)
        }
        spring.start()
    }

    private fun applyFrame(icon: View, progress: Float) {
        val remaining = max(0f, 1f - progress)

        if (remaining <= 0.005f) {
            icon.rotation = 0f
            icon.rotationY = 0f
            icon.scaleX = 1f
            icon.scaleY = 1f
            icon.alpha = 1f
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                icon.setRenderEffect(null)
            }
            return
        }

        icon.rotation = remaining * MAX_ROTATION_DEGREES
        icon.rotationY = remaining * 30f

        val enterScale = (1f + (OVERSHOOT_SCALE - 1f) *
                sin(progress * PI.toFloat()) * remaining + (1f - remaining))
            .coerceAtLeast(0.05f)
        icon.scaleX = enterScale
        icon.scaleY = enterScale
        icon.alpha = progress.coerceIn(0f, 1f)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val w = icon.width.toFloat().coerceAtLeast(50f)
            val h = icon.height.toFloat().coerceAtLeast(50f)
            val effect = CinematicShader.createCinematicEffect(
                width = w,
                height = h,
                rotationSpeed = remaining * 4.0f,
                scaleFactor = enterScale,
                blurIntensity = remaining * BLUR_MULTIPLIER,
                chromaticShift = remaining * CHROMATIC_MULTIPLIER,
                vignetteIntensity = remaining * VIGNETTE_MULTIPLIER
            )
            icon.setRenderEffect(effect)
        }
    }
}
