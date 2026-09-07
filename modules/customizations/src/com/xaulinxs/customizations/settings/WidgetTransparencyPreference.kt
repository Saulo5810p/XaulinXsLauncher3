/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.blur.XaulinXsWidgetTransparency
import com.xaulinxs.customizations.blur.XaulinXsWidgetTransparency.WIDGET_TRANSPARENCY_PERCENT

class WidgetTransparencyPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = XaulinXsWidgetTransparency.MIN_PERCENT
        max = XaulinXsWidgetTransparency.MAX_PERCENT
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(WIDGET_TRANSPARENCY_PERCENT)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(WIDGET_TRANSPARENCY_PERCENT, newValue as Int)
            true
        }
    }
}
