/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Interruptor "Véu temático no menu de apps": liga/desliga as manchas de cor
 * do wallpaper (WallpaperGradientView) atrás do menu de apps. É INDEPENDENTE
 * do "Fundo desfocado no menu de apps" (ThemedScrimPreference): o desfoque
 * continua ligado/desligado por ele; as cores só aparecem se o usuário ligar
 * este interruptor. Desligado por padrão.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

class ThemedVeilPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(THEMED_VEIL_ENABLED)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(THEMED_VEIL_ENABLED, newValue as Boolean)
            true
        }
    }

    companion object {
        private const val KEY_THEMED_VEIL_ENABLED = "xaulinxs_themed_veil_enabled"
        val THEMED_VEIL_ENABLED = backedUpItem(KEY_THEMED_VEIL_ENABLED, false)
    }
}
