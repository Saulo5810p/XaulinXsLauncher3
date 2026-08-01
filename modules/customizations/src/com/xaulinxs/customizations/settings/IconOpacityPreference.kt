/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.LauncherAppState
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.icons.XaulinXsIconOpacity
import com.xaulinxs.customizations.icons.XaulinXsIconOpacity.ICON_OPACITY_PERCENT

class IconOpacityPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = XaulinXsIconOpacity.MIN_PERCENT
        max = XaulinXsIconOpacity.MAX_PERCENT
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(ICON_OPACITY_PERCENT)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(ICON_OPACITY_PERCENT, newValue as Int)
            // XaulinXs Customizations: reaplica a opacidade em todos os ícones já na tela
            LauncherAppState.getInstance(context).model.forceReload("xaulinxs_icon_opacity_toggle")
            true
        }
    }
}
