/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 * XAULINXS_POPUPS_V4
 *
 * ScrollView com altura máxima, usada pelo popup de opções do ícone
 * (PopupContainerWithArrow) quando o conteúdo é mais alto que a tela: acima do limite
 * ela rola; abaixo, se comporta como wrap_content. Fade nas bordas indica que há mais
 * conteúdo (o fade de cima só aparece depois que o usuário rola para baixo).
 */
package com.xaulinxs.customizations.popup

import android.content.Context
import android.widget.ScrollView

class XaulinXsMaxHeightScrollView(
    context: Context,
    private val maxHeightPx: Int,
) : ScrollView(context) {

    init {
        isVerticalScrollBarEnabled = false
        overScrollMode = OVER_SCROLL_NEVER
        isVerticalFadingEdgeEnabled = true
        setFadingEdgeLength((FADE_DP * resources.displayMetrics.density).toInt())
        isFillViewport = false
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val mode = MeasureSpec.getMode(heightMeasureSpec)
        val size = MeasureSpec.getSize(heightMeasureSpec)
        val limit = if (mode == MeasureSpec.UNSPECIFIED) maxHeightPx else minOf(size, maxHeightPx)
        super.onMeasure(widthMeasureSpec, MeasureSpec.makeMeasureSpec(limit, MeasureSpec.AT_MOST))
    }

    private companion object {
        const val FADE_DP = 24f
    }
}
