/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 * XAULINXS_BLUR_V3
 *
 * Slider "Intensidade do desfoque do papel de parede" (categoria Menu de aplicativo).
 * Define o raio MÁXIMO (0 a 320 px) que o papel de parede alcança com o drawer
 * totalmente aberto; durante o arrasto o raio cresce de 0 até esse valor.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

class DrawerWallpaperBlurPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = MIN_PX
        max = MAX_PX
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(DRAWER_WALLPAPER_BLUR_PX).coerceIn(MIN_PX, MAX_PX)
        setOnPreferenceChangeListener { _, newValue ->
            // Lido a cada frame do próximo arrasto do drawer; não precisa forçar nada.
            LauncherPrefs.get(context).put(DRAWER_WALLPAPER_BLUR_PX, newValue as Int)
            true
        }
    }

    companion object {
        const val MIN_PX = 0
        const val MAX_PX = 320
        private const val KEY_DRAWER_WALLPAPER_BLUR_PX = "xaulinxs_drawer_wallpaper_blur_px"

        // Padrão 320 = intensidade que o desfoque sempre teve.
        val DRAWER_WALLPAPER_BLUR_PX = backedUpItem(KEY_DRAWER_WALLPAPER_BLUR_PX, MAX_PX)

        /** Raio máximo (px) do desfoque do wallpaper com o drawer aberto. */
        fun getMaxRadiusPx(context: Context): Float =
            LauncherPrefs.get(context).get(DRAWER_WALLPAPER_BLUR_PX)
                .coerceIn(MIN_PX, MAX_PX).toFloat()
    }
}
