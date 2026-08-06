/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.blur

import android.graphics.RenderEffect
import android.graphics.Shader
import android.os.Build
import android.view.View
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

object XaulinXsWidgetBlur {
    const val MIN_PERCENT = 0
    const val MAX_PERCENT = 100

    private const val KEY_INTENSITY = "xaulinxs_widget_blur_intensity"
    private const val MAX_BLUR_RADIUS_PX = 24f

    @JvmField
    val WIDGET_BLUR_INTENSITY = backedUpItem(KEY_INTENSITY, MIN_PERCENT)

    @JvmStatic
    fun applyTo(view: View) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return
        val intensity =
            LauncherPrefs.get(view.context).get(WIDGET_BLUR_INTENSITY).coerceIn(MIN_PERCENT, MAX_PERCENT)
        if (intensity <= 0) {
            view.setRenderEffect(null)
            return
        }
        val radius = (intensity / 100f) * MAX_BLUR_RADIUS_PX
        view.setRenderEffect(
            RenderEffect.createBlurEffect(radius, radius, Shader.TileMode.DECAL)
        )
    }
}
