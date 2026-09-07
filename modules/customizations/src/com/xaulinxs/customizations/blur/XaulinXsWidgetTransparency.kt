/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Transparência dos widgets (categoria "Widget" das configurações,
 * slider 0-100, pedida junto do fix do wallpaper próprio do app).
 * Independente do desfoque (XaulinXsWidgetBlur): desfoque usa
 * RenderEffect (borra o conteúdo do widget), transparência usa
 * View.setAlpha (deixa o widget mais "fraco"/see-through). As duas
 * podem ser combinadas sem conflito, pois mexem em propriedades
 * diferentes da View.
 */
package com.xaulinxs.customizations.blur

import android.view.View
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

object XaulinXsWidgetTransparency {
    const val MIN_PERCENT = 0
    const val MAX_PERCENT = 100

    private const val KEY_TRANSPARENCY = "xaulinxs_widget_transparency_percent"

    @JvmField
    val WIDGET_TRANSPARENCY_PERCENT = backedUpItem(KEY_TRANSPARENCY, MIN_PERCENT)

    /**
     * Aplica a transparência atual à View do widget. [percent] é
     * "o quanto o widget fica transparente": 0 = totalmente opaco
     * (padrão, sem mudança visual), 100 = totalmente invisível.
     */
    @JvmStatic
    fun applyTo(view: View) {
        val percent =
            LauncherPrefs.get(view.context).get(WIDGET_TRANSPARENCY_PERCENT)
                .coerceIn(MIN_PERCENT, MAX_PERCENT)
        view.alpha = 1f - (percent / 100f)
    }
}
