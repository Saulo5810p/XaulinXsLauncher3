/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Motion blur + aberração cromática reagindo à velocidade do arrasto entre
 * páginas/abas, portado do princípio já validado no projeto irmão
 * RetroPlayer Compose (CinematicScrollEffects.kt / cinematicScrollVelocity).
 *
 * Diferença de plataforma: o RetroPlayer aplica isso via Modifier.graphicsLayer
 * reagindo a LazyListState (Compose). Aqui não existe LazyListState — o
 * PagedView (base do Workspace) já expõe a mesma informação de velocidade
 * nativamente via OverScroller.getCurrVelocity() durante o fling, e via o
 * delta de posição a cada ACTION_MOVE durante o arrasto manual do dedo.
 * Esta classe centraliza a suavização (mesmo algoritmo de decaimento
 * exponencial do RetroPlayer) e a aplicação do RenderEffect na própria
 * PagedView/Workspace via setRenderEffect — sem tocar no scroll real.
 *
 * Perfil fixo INSANE (mesma decisão do RetroPlayer: sem versão reduzida).
 */
package com.xaulinxs.customizations.cinematic

import android.os.Build
import android.view.View
import kotlin.math.abs
import kotlin.math.min

object CinematicScrollVelocityEffect {

    // Mesmos multiplicadores do perfil INSANE do RetroPlayer
    // (ScrollCinematicProfile.INSANE em CinematicScrollEffects.kt).
    private const val BLUR_MULTIPLIER = 1.8f
    private const val CHROMATIC_MULTIPLIER = 1.6f
    private const val VIGNETTE_MULTIPLIER = 0.7f
    private const val VELOCITY_THRESHOLD = 450f

    // Mesma suavização exponencial do RetroPlayer: sobe rápido (resposta
    // imediata ao gesto), desce suave (o efeito "esvai" em vez de cortar
    // seco quando o dedo/fling para).
    private const val DECAY_KEEP = 0.82f
    private const val DECAY_NEW = 0.18f

    // WeakHashMap: evita reter a View (e sua Activity/Context) na memória
    // caso o Launcher recrie a PagedView (rotação, mudança de config) sem
    // que este objeto singleton seja notificado — a entrada é coletada
    // junto com a View quando não há mais nenhuma outra referência forte.
    private val states = java.util.WeakHashMap<View, State>()

    private class State {
        var lastOffset = 0f
        var smoothedVelocity = 0f
    }

    /**
     * Chamar a cada frame de scroll (arrasto manual OU fling do
     * OverScroller) com a posição de scroll absoluta atual em pixels.
     * Aplica o RenderEffect diretamente na `target` (tipicamente a própria
     * PagedView/Workspace) proporcional à velocidade suavizada.
     */
    @JvmStatic
    fun onScrollPositionChanged(target: View, absoluteScrollPx: Float) {
        val state = states.getOrPut(target) { State() }

        val delta = abs(absoluteScrollPx - state.lastOffset)
        state.lastOffset = absoluteScrollPx

        state.smoothedVelocity = if (delta > state.smoothedVelocity) {
            delta
        } else {
            state.smoothedVelocity * DECAY_KEEP + delta * DECAY_NEW
        }

        val velocity = min(state.smoothedVelocity / VELOCITY_THRESHOLD, 1f)
        applyEffect(target, velocity)
    }

    /**
     * Chamar quando o scroll termina de vez (fling concluído, dedo solto
     * sem fling) para garantir que o efeito zera mesmo sem mais eventos de
     * posição chegando.
     */
    @JvmStatic
    fun onScrollSettled(target: View) {
        states[target]?.smoothedVelocity = 0f
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            target.setRenderEffect(null)
        }
    }

    private fun applyEffect(target: View, velocity: Float) {
        // setRenderEffect(RenderEffect) só existe a partir da API 31 —
        // em aparelhos mais antigos (minSdk 28) este efeito específico
        // simplesmente não roda, sem crash e sem afetar o scroll real.
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return

        if (velocity < 0.02f) {
            target.setRenderEffect(null)
            return
        }
        val w = target.width.toFloat().coerceAtLeast(100f)
        val h = target.height.toFloat().coerceAtLeast(100f)

        val effect = CinematicShader.createCinematicEffect(
            width = w,
            height = h,
            rotationSpeed = 0f,
            scaleFactor = 1f,
            blurIntensity = velocity * BLUR_MULTIPLIER,
            chromaticShift = velocity * CHROMATIC_MULTIPLIER,
            vignetteIntensity = velocity * VIGNETTE_MULTIPLIER
        )
        target.setRenderEffect(effect)
    }
}
