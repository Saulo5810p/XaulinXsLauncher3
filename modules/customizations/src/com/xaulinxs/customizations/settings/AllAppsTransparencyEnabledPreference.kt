/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.theme.ALLAPPS_TRANSPARENCY_ENABLED
import com.xaulinxs.customizations.theme.XaulinXsAllAppsTransparencyRedraw

class AllAppsTransparencyEnabledPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(ALLAPPS_TRANSPARENCY_ENABLED)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(ALLAPPS_TRANSPARENCY_ENABLED, newValue as Boolean)
            XaulinXsAllAppsTransparencyRedraw.requestRedraw(context)
            true
        }
    }
}

// XAULINXS_ALLAPPS_TRANSPARENCY_ENABLED_PREFERENCE_FILE
