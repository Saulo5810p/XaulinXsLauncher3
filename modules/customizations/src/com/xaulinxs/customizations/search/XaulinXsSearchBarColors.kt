/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Cor de fundo/texto da barra de busca. Auto-suficiente de propósito: usa
 * cor própria da barra (se ativada) ou WallpaperColorHints como fallback —
 * NÃO depende de nenhuma classe da feature de editor de cor manual dos
 * ícones (feature 5, feita em outra sessão), porque essa API não pôde ser
 * verificada contra o código real no momento em que este script foi
 * escrito. Trocar a fonte de cor depois é uma mudança pequena e isolada
 * neste arquivo, se quiser unificar.
 */
package com.xaulinxs.customizations.search

import android.content.Context
import androidx.core.graphics.ColorUtils
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.Utilities
import com.android.launcher3.util.WallpaperColorHints

private const val SHADE_RATIO_LIGHT = 0.15f
private const val SHADE_RATIO_DARK = 0.55f
private val DEFAULT_FALLBACK_COLOR = 0xFF808080.toInt() // cinza neutro, só se não houver cor de wallpaper

object XaulinXsSearchBarColors {

    fun getBackgroundColor(context: Context): Int {
        val prefs = LauncherPrefs.get(context)
        val base = if (prefs.get(XaulinXsSearchBarPrefs.SEARCH_BAR_CUSTOM_COLOR_ENABLED)) {
            prefs.get(XaulinXsSearchBarPrefs.SEARCH_BAR_CUSTOM_COLOR_VALUE)
        } else {
            WallpaperColorHints.get(context).colors?.primaryColor?.toArgb() ?: DEFAULT_FALLBACK_COLOR
        }
        val isDark = Utilities.isDarkTheme(context)
        val shaded =
            if (isDark) {
                ColorUtils.blendARGB(base, android.graphics.Color.BLACK, SHADE_RATIO_DARK)
            } else {
                ColorUtils.blendARGB(base, android.graphics.Color.WHITE, SHADE_RATIO_LIGHT)
            }
        val opacityPercent = prefs.get(XaulinXsSearchBarPrefs.SEARCH_BAR_OPACITY).coerceIn(0, 100)
        val alpha = opacityPercent * 255 / 100
        return ColorUtils.setAlphaComponent(shaded, alpha)
    }

    fun getForegroundColor(context: Context): Int =
        if (Utilities.isDarkTheme(context)) android.graphics.Color.WHITE else android.graphics.Color.BLACK
}
