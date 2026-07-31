/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * O Android bloqueia (desde a API 33+) o acesso ao bitmap real do wallpaper
 * para apps de terceiros — decisão deliberada do Google. E o cross-window
 * blur (FLAG_BLUR_BEHIND) está desabilitado neste dispositivo pelo próprio
 * sistema (ver XaulinXsDepthController, addCrossWindowBlurEnabledListener).
 *
 * Sem acesso à imagem nem ao blur de janela, esta View simula um fundo
 * "vidro fosco" desenhando manchas radiais sobrepostas com as cores reais
 * extraídas do wallpaper (WallpaperColors.primaryColor/secondaryColor/
 * tertiaryColor — API pública, sem restrição), e aplica RenderEffect de
 * blur MUITO forte sobre o próprio desenho (blur local, processado pela
 * GPU do app — independente do cross-window blur do sistema).
 */
package com.xaulinxs.customizations.theme

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RadialGradient
import android.graphics.RenderEffect
import android.graphics.Shader
import android.os.Build
import android.util.AttributeSet
import android.view.View
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.util.OnColorHintListener
import com.android.launcher3.util.WallpaperColorHints
import com.xaulinxs.customizations.settings.ThemedScrimPreference.Companion.THEMED_SCRIM_ENABLED

private const val BLUR_RADIUS_PX = 220f

class WallpaperGradientView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs), OnColorHintListener {

    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)

    init {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            setRenderEffect(
                RenderEffect.createBlurEffect(BLUR_RADIUS_PX, BLUR_RADIUS_PX, Shader.TileMode.CLAMP)
            )
        }
    }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        WallpaperColorHints.get(context).registerOnColorHintsChangedListener(this)
    }

    override fun onDetachedFromWindow() {
        super.onDetachedFromWindow()
        WallpaperColorHints.get(context).unregisterOnColorsChangedListener(this)
    }

    override fun onColorHintsChanged(colorHints: Int) {
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (!LauncherPrefs.get(context).get(THEMED_SCRIM_ENABLED)) return
        val colors = WallpaperColorHints.get(context).colors ?: return
        val w = width.toFloat()
        val h = height.toFloat()
        if (w <= 0f || h <= 0f) return

        val primary = colors.primaryColor.toArgb()
        val secondary = (colors.secondaryColor ?: colors.primaryColor).toArgb()
        val tertiary = (colors.tertiaryColor ?: colors.secondaryColor ?: colors.primaryColor).toArgb()

        drawBlob(canvas, primary, w * 0.2f, h * 0.15f, w * 0.9f)
        drawBlob(canvas, secondary, w * 0.85f, h * 0.4f, w * 0.9f)
        drawBlob(canvas, tertiary, w * 0.4f, h * 0.9f, w * 0.9f)
    }

    private fun drawBlob(canvas: Canvas, color: Int, cx: Float, cy: Float, radius: Float) {
        paint.shader = RadialGradient(
            cx, cy, radius,
            color, android.graphics.Color.TRANSPARENT,
            Shader.TileMode.CLAMP
        )
        canvas.drawCircle(cx, cy, radius, paint)
    }
}
