/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.blur.XaulinXsWidgetBlur
import com.xaulinxs.customizations.blur.XaulinXsWidgetBlur.WIDGET_BLUR_INTENSITY

class WidgetBlurPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = XaulinXsWidgetBlur.MIN_PERCENT
        max = XaulinXsWidgetBlur.MAX_PERCENT
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(WIDGET_BLUR_INTENSITY)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(WIDGET_BLUR_INTENSITY, newValue as Int)
            true
        }
    }
}
