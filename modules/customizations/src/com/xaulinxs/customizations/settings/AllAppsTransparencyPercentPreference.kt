/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.theme.ALLAPPS_TRANSPARENCY_MAX_PERCENT
import com.xaulinxs.customizations.theme.ALLAPPS_TRANSPARENCY_MIN_PERCENT
import com.xaulinxs.customizations.theme.ALLAPPS_TRANSPARENCY_PERCENT
import com.xaulinxs.customizations.theme.XaulinXsAllAppsTransparencyRedraw

class AllAppsTransparencyPercentPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = ALLAPPS_TRANSPARENCY_MIN_PERCENT
        max = ALLAPPS_TRANSPARENCY_MAX_PERCENT
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(ALLAPPS_TRANSPARENCY_PERCENT)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(ALLAPPS_TRANSPARENCY_PERCENT, newValue as Int)
            XaulinXsAllAppsTransparencyRedraw.requestRedraw(context)
            true
        }
    }
}

// XAULINXS_ALLAPPS_TRANSPARENCY_PERCENT_PREFERENCE_FILE
