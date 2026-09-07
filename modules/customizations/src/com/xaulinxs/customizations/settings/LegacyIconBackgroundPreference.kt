/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.icons.XaulinXsLegacyIconAppearance

class LegacyIconBackgroundPreference
@JvmOverloads
constructor(context: Context, attrs: AttributeSet? = null) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked =
            LauncherPrefs.get(context).get(XaulinXsLegacyIconAppearance.LEGACY_ICON_BG_SHADOW_REMOVED)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context)
                .put(XaulinXsLegacyIconAppearance.LEGACY_ICON_BG_SHADOW_REMOVED, newValue as Boolean)
            // XaulinXs: assim como as demais preferences deste módulo que
            // mexem em BitmapInfo (ex.: ícones temáticos), o efeito aparece
            // para ícones recalculados a partir de agora — o cache de
            // ícones já gerados anteriormente só é reconstruído quando o
            // sistema naturalmente invalida essas entradas (ex.: reabrir o
            // launcher). Não há, neste projeto, um mecanismo de "recarregar
            // cache de ícones na hora" para reaproveitar.
            true
        }
    }
}
