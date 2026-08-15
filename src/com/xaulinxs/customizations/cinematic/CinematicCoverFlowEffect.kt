/*
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
    // XAULINXS_NAN_CRASH_FIX_APPLIED
    @JvmStatic
    fun applyToPage(page: View, scrollProgress: Float) {
        // Guarda contra NaN/Infinity: getScrollProgress() nativo do
        // PagedView divide por totalDistance (largura medida da página
        // vizinha), que ainda é 0 na primeíssima inserção de tela
        // (Workspace.bindAndInitFirstWorkspaceScreen chama
        // updatePageScrollValues() antes do primeiro onMeasure/onLayout
        // rodar). 0/0 = NaN, delta/0 = Infinity — coerceIn NÃO filtra
        // NaN (qualquer comparação com NaN é false, passa direto) e
        // View.setScaleX/setRotationY lançam IllegalArgumentException
        // pra qualquer valor não-finito. Sem isso o launcher crasha ao
        // abrir. Resposta segura: página fica no estado neutro (sem
        // rotação/perspectiva) até o layout estar medido de verdade —
        // a próxima chamada real de scroll corrige a transformação.
        if (!scrollProgress.isFinite()) {
            resetPage(page)
            return
        }

        val pageOffset = scrollProgress.coerceIn(-1.4f, 1.4f)
        val absOffset = abs(pageOffset)

        val rotationY = (pageOffset * ROTATION_MULTIPLIER)
            .coerceIn(-ROTATION_MAX, ROTATION_MAX) + (GyroTiltProvider.tiltX * 0.55f)
        val scale = (SCALE_BASE - (absOffset * SCALE_FALLOFF)).coerceIn(SCALE_MIN, SCALE_MAX)
        val alpha = (1f - (absOffset * ALPHA_FALLOFF)).coerceIn(ALPHA_MIN, 1f)

        // Segunda guarda: cameraDistance depende de resources/displayMetrics,
        // que também pode devolver density 0 em contextos degenerados
        // (ex.: view ainda não anexada). Se algo aqui não for finito,
        // aplica só rotação/escala/alpha (já garantidos finitos acima) e
        // pula a perspectiva em vez de arriscar outro crash.
        val density = page.resources?.displayMetrics?.density ?: 0f
        if (density.isFinite() && density > 0f) {
            page.cameraDistance = CAMERA_DISTANCE_DP * density
        }
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

// XAULINXS_COVERFLOW_EFFECT_FILE
