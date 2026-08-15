/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Blur pesado e progressivo por PÁGINA do Workspace, reagindo à posição
 * de scroll (quão no meio do caminho entre duas páginas ela está) — não
 * à velocidade do gesto. Diferente e mais pesado que
 * CinematicScrollVelocityEffect (feature 2, aplicado na PagedView inteira,
 * raio máximo 60f, reage a velocidade): este aplica direto em cada
 * CellLayout via RenderEffect.createBlurEffect puro, raio até 300f no
 * pico (meio do caminho entre páginas), TileMode.DECAL (borra e deixa
 * transparente fora dos limites da página, "vazando" a mancha de blur).
 *
 * Decisão confirmada com o usuário: os dois efeitos ficam SEPARADOS (não
 * fundidos num raio só) — o de velocidade continua exatamente como está
 * hoje na PagedView inteira (aberração cromática/vinheta incluídas,
 * perfeito reagindo ao arrasto). Este é um efeito adicional, empilhado
 * visualmente por estar numa view filha (CellLayout) dentro da PagedView
 * — native compositing do Android soma as duas camadas de blur sem
 * precisar de nenhum código de composição manual.
 *
 * setRenderEffect(null) quando a página está praticamente centralizada
 * (scrollProgress ~0), recuperando nitidez total — sem nenhuma trava de
 * "só atualiza se mudou", reage a cada frame de scroll conforme pedido.
 *
 * Guarda isFinite() desde a primeira versão (aprendizado da feature 7:
 * getScrollProgress() pode devolver NaN/Infinity antes do primeiro
 * layout medido — sem essa guarda o launcher crasha ao abrir).
 */
package com.xaulinxs.customizations.cinematic

import android.graphics.Shader
import android.os.Build
import android.view.View
import kotlin.math.abs

object WorkspaceDepthBlurEffect {

    // Raio máximo de blur no pico (scrollProgress = ±1, meio do caminho
    // entre duas páginas) — pedido explícito do usuário: "bruto", cobrindo
    // ícones e widgets por completo.
    private const val MAX_BLUR_RADIUS = 300f
    private const val MIN_BLUR_RADIUS = 0.5f // abaixo disso, remove o efeito (evita RenderEffect inútil)

    /**
     * Chamar para cada página (CellLayout) a cada recálculo de scroll —
     * mesmo ponto e mesmo scrollProgress já usados por
     * CinematicCoverFlowEffect.applyToPage em
     * Workspace.updatePageScrollValues().
     */
    @JvmStatic
    fun applyToPage(page: View, scrollProgress: Float) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return

        // Mesma guarda que evitou o crash da feature 7: scrollProgress
        // pode vir NaN/Infinity antes do primeiro layout medido.
        if (!scrollProgress.isFinite()) {
            page.setRenderEffect(null)
            return
        }

        val absProgress = abs(scrollProgress).coerceIn(0f, 1.4f)
        val radius = absProgress * MAX_BLUR_RADIUS

        if (radius < MIN_BLUR_RADIUS) {
            page.setRenderEffect(null)
            return
        }

        val effect = android.graphics.RenderEffect.createBlurEffect(
            radius,
            radius,
            Shader.TileMode.DECAL
        )
        page.setRenderEffect(effect)
    }
}

// XAULINXS_WORKSPACE_DEPTH_BLUR_FILE
