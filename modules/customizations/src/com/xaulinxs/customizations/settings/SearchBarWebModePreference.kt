/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.search.XaulinXsSearchBarPrefs

class SearchBarWebModePreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(XaulinXsSearchBarPrefs.SEARCH_BAR_WEB_MODE)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(XaulinXsSearchBarPrefs.SEARCH_BAR_WEB_MODE, newValue as Boolean)
            true
        }
    }
}
