/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 * XAULINXS_BLUR_V2
 *
 * "Ícones desfocados": desfoque ESTÁTICO (0-200%) aplicado só ao ícone de todo
 * BubbleTextView — home, hotseat, pastas abertas e menu de apps. Não tem
 * relação nenhuma com o desfoque do arrasto de abrir/fechar o app drawer
 * (XaulinXsDepthController), que não é tocado por esta feature.
 *
 * Como funciona: BubbleTextView.applyCompoundDrawables() passa o ícone por
 * wrapIfNeeded(). Com a feature desligada (ou em 0%) devolve o próprio ícone,
 * ou seja, o comportamento é idêntico ao original. Ligada, embrulha o ícone num
 * Drawable que o desenha dentro de um RenderNode com RenderEffect de blur
 * (só o ícone; o texto do label continua nítido).
 */
package com.xaulinxs.customizations.icons

import android.content.Context
import android.graphics.Canvas
import android.graphics.ColorFilter
import android.graphics.PixelFormat
import android.graphics.Rect
import android.graphics.RenderEffect
import android.graphics.RenderNode
import android.graphics.Shader
import android.graphics.drawable.Drawable
import android.os.Build
import androidx.annotation.RequiresApi
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem
import com.android.launcher3.icons.FastBitmapDrawable

object XaulinXsIconBlur {
    private const val KEY_ICON_BLUR_ENABLED = "xaulinxs_icon_blur_enabled"
    private const val KEY_ICON_BLUR_PERCENT = "xaulinxs_icon_blur_percent"

    const val MIN_PERCENT = 0
    const val MAX_PERCENT = 200
    const val DEFAULT_PERCENT = 100

    // Raio do desfoque a 100%, em dp (200% = o dobro). É a única constante a
    // mexer se quiser o desfoque dos ícones mais forte ou mais fraco.
    const val BASE_RADIUS_DP = 6f

    // Desligado por padrão: nada muda visualmente até o usuário ligar.
    @JvmField
    val ICON_BLUR_ENABLED = backedUpItem(KEY_ICON_BLUR_ENABLED, false)

    @JvmField
    val ICON_BLUR_PERCENT = backedUpItem(KEY_ICON_BLUR_PERCENT, DEFAULT_PERCENT)

    /** Raio atual em px; 0 se desligado, 0%, ou Android < 12. */
    @JvmStatic
    fun getRadiusPx(context: Context): Float {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return 0f
        val prefs = LauncherPrefs.get(context)
        if (!prefs.get(ICON_BLUR_ENABLED)) return 0f
        val percent = prefs.get(ICON_BLUR_PERCENT).coerceIn(MIN_PERCENT, MAX_PERCENT)
        return BASE_RADIUS_DP * context.resources.displayMetrics.density * percent / 100f
    }

    /** Chamado por BubbleTextView.applyCompoundDrawables(). */
    @JvmStatic
    fun wrapIfNeeded(context: Context, icon: Drawable): Drawable {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return icon
        // Só ícones reais; o ColorDrawable transparente de "ícone oculto" fica como está.
        if (icon !is FastBitmapDrawable) return icon
        val radiusPx = getRadiusPx(context)
        if (radiusPx < 1f) return icon
        val wrapper = XaulinXsBlurIconDrawable(icon, radiusPx)
        // O TextView lê os bounds do drawable ao medir; o wrapper nasce com os do ícone.
        wrapper.setBounds(icon.bounds)
        return wrapper
    }
}

@RequiresApi(Build.VERSION_CODES.S)
class XaulinXsBlurIconDrawable(
    private val inner: Drawable,
    private val radiusPx: Float,
) : Drawable(), Drawable.Callback {

    private val node = RenderNode("xaulinxs_icon_blur")
    private val padPx = Math.ceil((radiusPx * 3f).toDouble()).toInt()

    init {
        inner.setCallback(this)
        node.setRenderEffect(
            RenderEffect.createBlurEffect(radiusPx, radiusPx, Shader.TileMode.CLAMP)
        )
    }

    override fun onBoundsChange(bounds: Rect) {
        inner.setBounds(bounds)
    }

    override fun draw(canvas: Canvas) {
        val b = bounds
        if (b.isEmpty || !canvas.isHardwareAccelerated) {
            // Canvas de software (ex.: render em Bitmap): sem RenderEffect, desenha normal.
            inner.draw(canvas)
            return
        }
        // O RenderNode é maior que o ícone (padPx de cada lado) para o blur não ser cortado.
        val w = b.width() + 2 * padPx
        val h = b.height() + 2 * padPx
        node.setPosition(0, 0, w, h)
        val rc = node.beginRecording(w, h)
        try {
            rc.translate((padPx - b.left).toFloat(), (padPx - b.top).toFloat())
            inner.draw(rc)
        } finally {
            node.endRecording()
        }
        val count = canvas.save()
        canvas.translate((b.left - padPx).toFloat(), (b.top - padPx).toFloat())
        canvas.drawRenderNode(node)
        canvas.restoreToCount(count)
    }

    override fun setAlpha(alpha: Int) {
        inner.setAlpha(alpha)
    }

    override fun getAlpha(): Int = inner.getAlpha()

    override fun setColorFilter(colorFilter: ColorFilter?) {
        inner.setColorFilter(colorFilter)
    }

    @Suppress("DEPRECATION")
    override fun getOpacity(): Int = PixelFormat.TRANSLUCENT

    override fun getIntrinsicWidth(): Int = inner.intrinsicWidth

    override fun getIntrinsicHeight(): Int = inner.intrinsicHeight

    override fun isStateful(): Boolean = inner.isStateful

    override fun onStateChange(state: IntArray): Boolean = inner.setState(state)

    override fun onLevelChange(level: Int): Boolean = inner.setLevel(level)

    override fun setVisible(visible: Boolean, restart: Boolean): Boolean {
        inner.setVisible(visible, restart)
        return super.setVisible(visible, restart)
    }

    override fun invalidateDrawable(who: Drawable) {
        invalidateSelf()
    }

    override fun scheduleDrawable(who: Drawable, what: Runnable, `when`: Long) {
        scheduleSelf(what, `when`)
    }

    override fun unscheduleDrawable(who: Drawable, what: Runnable) {
        unscheduleSelf(what)
    }
}
