/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

class ThemedScrimPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(THEMED_SCRIM_ENABLED)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(THEMED_SCRIM_ENABLED, newValue as Boolean)
            true
        }
    }

    companion object {
        private const val KEY_THEMED_SCRIM_ENABLED = "xaulinxs_themed_scrim_enabled"
        val THEMED_SCRIM_ENABLED = backedUpItem(KEY_THEMED_SCRIM_ENABLED, true)
    }
}
