/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Efeito visual de giro/blur/escala ao tocar em um ícone, portado do
 * princípio já validado no RetroPlayer Compose (cinematicPressVisuals):
 * reage ao evento de toque JÁ CAPTURADO pela view real, nunca intercepta
 * ou consome o toque. O clique/long-press nativo do BubbleTextView
 * continua funcionando exatamente como antes — este efeito só observa.
 *
 * Perfil fixo "INSANE" (sem versão reduzida), mesmo princípio do projeto
 * irmão: giro leve em rotationY, escala de destaque, e blur real via
 * RenderEffect quando o aparelho suporta (API 31+); em API 28-30 o giro
 * e a escala continuam, só o blur é omitido (RenderEffect não existe
 * antes de API 31 — omitir aqui não é redução de efeito, é o hardware
 * mais antigo simplesmente não ter o recurso).
 */
package com.xaulinxs.customizations.cinematic

import android.animation.Animator
import android.animation.AnimatorListenerAdapter
import android.animation.ValueAnimator
import android.animation.ObjectAnimator
import android.animation.AnimatorSet
import android.graphics.RenderEffect
import android.graphics.Shader
import android.os.Build
import android.view.MotionEvent
import android.view.View
import android.view.animation.DecelerateInterpolator
import android.view.animation.OvershootInterpolator

object CinematicPressEffects {

    private const val ROTATION_DEGREES = 12f
    private const val SCALE_PEAK = 1.12f
    private const val BLUR_RADIUS_PX = 6f
    private const val DURATION_DOWN_MS = 90L
    private const val DURATION_UP_MS = 220L

    // Evita empilhar animações concorrentes na mesma view se o usuário
    // tocar rápido várias vezes seguidas.
    private val activeAnimators = HashMap<View, AnimatorSet>()

    /**
     * Chamar a partir do onTouchEvent/onDelegateTouchEvent JÁ EXISTENTE,
     * sempre DEPOIS (ou em paralelo, nunca em vez) de deixar a view real
     * processar o evento. Este método nunca retorna valor e nunca chama
     * event.setAction()/consome o evento — é puramente reativo.
     */
    @JvmStatic
    fun onTouchObserved(target: View, event: MotionEvent) {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> pressIn(target)
            MotionEvent.ACTION_UP,
            MotionEvent.ACTION_CANCEL -> pressOut(target)
        }
    }

    private fun pressIn(target: View) {
        activeAnimators[target]?.cancel()

        applyBlur(target, BLUR_RADIUS_PX)

        val rotate = ObjectAnimator.ofFloat(target, View.ROTATION_Y, 0f, ROTATION_DEGREES)
        val scaleX = ObjectAnimator.ofFloat(target, View.SCALE_X, target.scaleX, SCALE_PEAK)
        val scaleY = ObjectAnimator.ofFloat(target, View.SCALE_Y, target.scaleY, SCALE_PEAK)

        val set = AnimatorSet()
        set.playTogether(rotate, scaleX, scaleY)
        set.duration = DURATION_DOWN_MS
        set.interpolator = DecelerateInterpolator()
        set.addListener(object : AnimatorListenerAdapter() {
            override fun onAnimationEnd(animation: Animator) {
                activeAnimators.remove(target)
            }
        })
        activeAnimators[target] = set
        set.start()
    }

    private fun pressOut(target: View) {
        activeAnimators[target]?.cancel()

        val rotateBack = ObjectAnimator.ofFloat(target, View.ROTATION_Y, target.rotationY, 0f)
        val scaleBackX = ObjectAnimator.ofFloat(target, View.SCALE_X, target.scaleX, 1f)
        val scaleBackY = ObjectAnimator.ofFloat(target, View.SCALE_Y, target.scaleY, 1f)

        val set = AnimatorSet()
        set.playTogether(rotateBack, scaleBackX, scaleBackY)
        set.duration = DURATION_UP_MS
        set.interpolator = OvershootInterpolator(1.5f)
        set.addListener(object : AnimatorListenerAdapter() {
            override fun onAnimationEnd(animation: Animator) {
                applyBlur(target, 0f)
                activeAnimators.remove(target)
            }
        })
        activeAnimators[target] = set
        set.start()
    }

    private fun applyBlur(target: View, radiusPx: Float) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) {
            // RenderEffect não existe antes da API 31 — giro/escala seguem
            // funcionando normalmente, só o blur fica de fora neste
            // aparelho especificamente.
            return
        }
        if (radiusPx <= 0f) {
            target.setRenderEffect(null)
            return
        }
        target.setRenderEffect(
            RenderEffect.createBlurEffect(radiusPx, radiusPx, Shader.TileMode.CLAMP)
        )
    }
}
