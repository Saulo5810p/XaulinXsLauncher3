/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Desenha o wallpaper PRÓPRIO do R's Home3 (ver XaulinXsInAppWallpaper)
 * como plano de fundo da tela inicial. É colocada como o primeiro filho
 * do DragLayer em res/layout/launcher.xml — ou seja, o mais no fundo
 * possível, atrás até do Workspace — então ela ocupa visualmente o lugar
 * onde o wallpaper real do sistema apareceria, mesmo sem mudar nenhuma
 * flag de transparência de janela.
 *
 * Escala em center-crop (preenche a View inteira, cortando o excesso,
 * sem distorcer) — o mesmo comportamento visual de um wallpaper normal.
 */
package com.xaulinxs.customizations.theme

import android.content.Context
import android.graphics.Canvas
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.RenderEffect
import android.graphics.Shader
import android.os.Build
import android.util.AttributeSet
import android.view.View

class XaulinXsWallpaperView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {

    private val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
    private val matrix = Matrix()
    private val onWallpaperChanged: () -> Unit = { post { invalidate() } }
    private val onBlurPrefChanged: () -> Unit = { post { applyBlurEffect() } }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        XaulinXsInAppWallpaper.addOnChangedListener(onWallpaperChanged)
        XaulinXsWorkspaceBlur.addOnChangedListener(onBlurPrefChanged)
        applyBlurEffect()
    }

    override fun onDetachedFromWindow() {
        super.onDetachedFromWindow()
        XaulinXsInAppWallpaper.removeOnChangedListener(onWallpaperChanged)
        XaulinXsWorkspaceBlur.removeOnChangedListener(onBlurPrefChanged)
    }

    /**
     * XaulinXs feature (info.txt/etapa 3: "Área de trabalho [...] -
     * desfoque"): usa View.setRenderEffect (RenderNode blur, API 31+),
     * que roda inteiramente dentro da NOSSA janela — diferente do blur
     * "de vidro fosco" das outras telas (balões/menu de apps/widgets),
     * que depende de cross-window blur do sistema e já está documentado
     * como bloqueado pelo ROM deste aparelho (ver XaulinXsDepthController).
     * Por desenharmos o próprio wallpaper agora (XaulinXsInAppWallpaper),
     * dá pra aplicar esse blur sem depender de nenhuma permissão ou
     * capability do sistema.
     */
    private fun applyBlurEffect() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return
        val radiusPx = XaulinXsWorkspaceBlur.getBlurRadiusPx(context)
        setRenderEffect(
            if (radiusPx > 0f)
                RenderEffect.createBlurEffect(radiusPx, radiusPx, Shader.TileMode.CLAMP)
            else null
        )
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val bitmap = XaulinXsInAppWallpaper.getCurrentWallpaper(context) ?: return
        val viewW = width.toFloat()
        val viewH = height.toFloat()
        if (viewW <= 0f || viewH <= 0f) return

        val bmpW = bitmap.width.toFloat()
        val bmpH = bitmap.height.toFloat()
        // center-crop: escala pelo maior fator entre largura/altura, pra
        // preencher a View inteira, e centraliza o excesso cortado.
        val scale = maxOf(viewW / bmpW, viewH / bmpH)
        val scaledW = bmpW * scale
        val scaledH = bmpH * scale
        matrix.reset()
        matrix.setScale(scale, scale)
        matrix.postTranslate((viewW - scaledW) / 2f, (viewH - scaledH) / 2f)
        canvas.drawBitmap(bitmap, matrix, paint)
    }
}
