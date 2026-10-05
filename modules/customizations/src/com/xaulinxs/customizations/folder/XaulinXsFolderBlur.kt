/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * "Pastas desfocadas": o MESMO desfoque estático dos ícones (XaulinXsIconBlur) aplicado ao
 * ícone de pasta da tela inicial/hotseat — fundo, ícones em miniatura e borda. O nome da
 * pasta e a bolinha de notificação continuam nítidos. Mesmos valores: raio base de 6dp a
 * 100%, slider de 0 a 200%. Desligado por padrão; abaixo do Android 12 não faz nada.
 */
package com.xaulinxs.customizations.folder

import android.content.Context
import android.graphics.Canvas
import android.graphics.RenderEffect
import android.graphics.RenderNode
import android.graphics.Shader
import android.os.Build
import androidx.annotation.RequiresApi
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem
import com.xaulinxs.customizations.icons.XaulinXsIconBlur
import java.util.function.Consumer

object XaulinXsFolderBlur {
    const val MIN_PERCENT = XaulinXsIconBlur.MIN_PERCENT
    const val MAX_PERCENT = XaulinXsIconBlur.MAX_PERCENT
    const val DEFAULT_PERCENT = XaulinXsIconBlur.DEFAULT_PERCENT

    @JvmField
    val FOLDER_BLUR_ENABLED = backedUpItem("xaulinxs_folder_blur_enabled", false)

    @JvmField
    val FOLDER_BLUR_PERCENT = backedUpItem("xaulinxs_folder_blur_percent", DEFAULT_PERCENT)

    /** Raio atual em px; 0 se desligado, 0%, ou Android < 12. Mesma fórmula dos ícones. */
    @JvmStatic
    fun getRadiusPx(context: Context): Float {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return 0f
        val prefs = LauncherPrefs.get(context)
        if (!prefs.get(FOLDER_BLUR_ENABLED)) return 0f
        val percent = prefs.get(FOLDER_BLUR_PERCENT).coerceIn(MIN_PERCENT, MAX_PERCENT)
        return XaulinXsIconBlur.BASE_RADIUS_DP * context.resources.displayMetrics.density * percent / 100f
    }
}

/** Desenha um trecho de conteúdo dentro de um RenderNode com RenderEffect de blur. */
@RequiresApi(Build.VERSION_CODES.S)
class XaulinXsFolderBlurLayer {
    private val node = RenderNode("xaulinxs_folder_blur")
    private var appliedRadius = -1f

    fun draw(canvas: Canvas, width: Int, height: Int, radiusPx: Float, content: Consumer<Canvas>) {
        if (radiusPx != appliedRadius) {
            node.setRenderEffect(RenderEffect.createBlurEffect(radiusPx, radiusPx, Shader.TileMode.CLAMP))
            appliedRadius = radiusPx
        }
        // O node é maior que a view (pad de cada lado) para o blur não ser cortado nas bordas.
        val pad = Math.ceil((radiusPx * 3f).toDouble()).toInt()
        val w = width + 2 * pad
        val h = height + 2 * pad
        node.setPosition(0, 0, w, h)
        val rc = node.beginRecording(w, h)
        try {
            rc.translate(pad.toFloat(), pad.toFloat())
            content.accept(rc)
        } finally {
            node.endRecording()
        }
        val count = canvas.save()
        canvas.translate(-pad.toFloat(), -pad.toFloat())
        canvas.drawRenderNode(node)
        canvas.restoreToCount(count)
    }
}
