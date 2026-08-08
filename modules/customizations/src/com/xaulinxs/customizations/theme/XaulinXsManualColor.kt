/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Fonte de cor manual (Feature 5). Quando ativada, esta cor fixa escolhida
 * pelo usuário substitui a cor extraída do wallpaper (WallpaperColorHints)
 * como cor-base tanto para os ícones temáticos (XaulinXsThemedIconColors)
 * quanto para o fundo/scrim do App Drawer (WallpaperScrimHelper) — os dois
 * continuam aplicando o mesmo sombreamento claro/escuro de sempre, só muda
 * de onde vem a cor de entrada.
 */
package com.xaulinxs.customizations.theme

import android.content.Context
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

object XaulinXsManualColor {

    private const val KEY_ENABLED = "xaulinxs_manual_color_enabled"
    private const val KEY_VALUE = "xaulinxs_manual_color_value"

    private const val DEFAULT_COLOR = 0xFF6750A4.toInt() // roxo Material, ARGB opaco

    val MANUAL_COLOR_ENABLED = backedUpItem(KEY_ENABLED, false)
    val MANUAL_COLOR_VALUE = backedUpItem(KEY_VALUE, DEFAULT_COLOR)

    /** Cor-base manual (ARGB opaco) se o modo estiver ativado, senão null. */
    @JvmStatic
    fun getBaseColorIfEnabled(context: Context): Int? {
        val prefs = LauncherPrefs.get(context)
        if (!prefs.get(MANUAL_COLOR_ENABLED)) return null
        return prefs.get(MANUAL_COLOR_VALUE)
    }
}
