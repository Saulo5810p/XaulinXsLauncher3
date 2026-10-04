/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 * XAULINXS_BLUR_V2
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.LauncherAppState
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.icons.XaulinXsIconBlur

class IconBlurPercentPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = XaulinXsIconBlur.MIN_PERCENT
        max = XaulinXsIconBlur.MAX_PERCENT
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(XaulinXsIconBlur.ICON_BLUR_PERCENT)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(XaulinXsIconBlur.ICON_BLUR_PERCENT, newValue as Int)
            LauncherAppState.getInstance(context).model.forceReload("xaulinxs_icon_blur_percent")
            true
        }
    }
}
