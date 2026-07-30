/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Calcula a cor de véu ("vidro fosco") usada atrás do App Drawer, a partir
 * da cor extraída do wallpaper via WallpaperColorHints. O alpha parcial é
 * essencial: é o que permite o RenderEffect de blur (ver
 * XaulinXsDepthController) aparecer através do véu, criando o efeito de
 * vidro fosco em vez de esconder tudo atrás de uma cor sólida.
 *
 * getScrimColorIfEnabled() é chamado diretamente por AllAppsState.java
 * (AOSP), que é a origem "de verdade" da cor do scrim consumida pela
 * animação de transição de estado.
 */
package com.xaulinxs.customizations.theme

import android.content.Context
import androidx.core.graphics.ColorUtils
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.Utilities
import com.android.launcher3.util.WallpaperColorHints
import com.xaulinxs.customizations.settings.ThemedScrimPreference.Companion.THEMED_SCRIM_ENABLED

private const val SCRIM_ALPHA_LIGHT = 140
private const val SCRIM_ALPHA_DARK = 160
private const val SHADE_RATIO_LIGHT = 0.15f
private const val SHADE_RATIO_DARK = 0.55f

object WallpaperScrimHelper {

    @JvmStatic
    fun getScrimColorIfEnabled(context: Context): Int? {
        if (!LauncherPrefs.get(context).get(THEMED_SCRIM_ENABLED)) return null
        return getScrimColor(context)
    }

    fun getScrimColor(context: Context): Int? {
        val primaryColor = WallpaperColorHints.get(context).colors?.primaryColor?.toArgb() ?: return null
        val isDark = Utilities.isDarkTheme(context)
        val shaded =
            if (isDark) {
                ColorUtils.blendARGB(primaryColor, android.graphics.Color.BLACK, SHADE_RATIO_DARK)
            } else {
                ColorUtils.blendARGB(primaryColor, android.graphics.Color.WHITE, SHADE_RATIO_LIGHT)
            }
        val alpha = if (isDark) SCRIM_ALPHA_DARK else SCRIM_ALPHA_LIGHT
        return ColorUtils.setAlphaComponent(shaded, alpha)
    }
}
