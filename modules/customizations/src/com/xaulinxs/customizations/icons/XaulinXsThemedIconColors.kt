/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * O AOSP resolve as cores dos ícones monocromáticos a partir de recursos
 * estáticos que, em compileSdk 31+, apontam para
 * @android:color/system_accent1_* — cores dinâmicas do sistema que não são
 * atualizadas neste dispositivo (ROMs não-Pixel não aplicam o overlay
 * Material You do AOSP), então a cor final é sempre o fallback hardcoded
 * do framework, independente do papel de parede.
 *
 * Esta classe calcula a mesma paleta (fundo + glifo) diretamente a partir
 * de WallpaperColorHints, igual ao resto das customizações XaulinXs.
 */
package com.xaulinxs.customizations.icons

import android.content.Context
import androidx.core.graphics.ColorUtils
import com.android.launcher3.Utilities
import com.android.launcher3.icons.mono.ColorList
import com.android.launcher3.util.WallpaperColorHints

private const val BG_SHADE_RATIO_LIGHT = 0.20f
private const val BG_SHADE_RATIO_DARK = 0.65f
private const val FG_SHADE_RATIO_LIGHT = 0.55f
private const val FG_SHADE_RATIO_DARK = 0.15f

object XaulinXsThemedIconColors {

    fun getColorsIfAvailable(context: Context): ColorList? {
        val primary = WallpaperColorHints.get(context).colors?.primaryColor?.toArgb() ?: return null
        val isDark = Utilities.isDarkTheme(context)

        val background =
            if (isDark) {
                ColorUtils.blendARGB(primary, android.graphics.Color.BLACK, BG_SHADE_RATIO_DARK)
            } else {
                ColorUtils.blendARGB(primary, android.graphics.Color.WHITE, BG_SHADE_RATIO_LIGHT)
            }
        val foreground =
            if (isDark) {
                ColorUtils.blendARGB(primary, android.graphics.Color.WHITE, 1f - FG_SHADE_RATIO_DARK)
            } else {
                ColorUtils.blendARGB(primary, android.graphics.Color.BLACK, FG_SHADE_RATIO_LIGHT)
            }

        return ColorList(
            iconBackgroundColor = background,
            iconForegroundColor = foreground,
            iconAdaptiveBackgroundColor = background,
            badgeBackgroundColor = background,
            badgeForegroundColor = foreground,
        )
    }
}
