/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 * XAULINXS_BLUR_V2
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherAppState
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.icons.XaulinXsIconBlur

class IconBlurEnabledPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(XaulinXsIconBlur.ICON_BLUR_ENABLED)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(XaulinXsIconBlur.ICON_BLUR_ENABLED, newValue as Boolean)
            // Mesmo padrão da opacidade dos ícones: rebinda todos os ícones já na tela.
            LauncherAppState.getInstance(context).model.forceReload("xaulinxs_icon_blur_toggle")
            true
        }
    }
}
