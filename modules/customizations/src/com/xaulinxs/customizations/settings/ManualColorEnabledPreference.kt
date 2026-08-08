/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.theme.XaulinXsManualColor

class ManualColorEnabledPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(XaulinXsManualColor.MANUAL_COLOR_ENABLED)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(XaulinXsManualColor.MANUAL_COLOR_ENABLED, newValue as Boolean)
            true
        }
    }
}
