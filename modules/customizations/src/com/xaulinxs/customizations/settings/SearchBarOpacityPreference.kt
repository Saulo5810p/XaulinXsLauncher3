/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.search.XaulinXsSearchBarPrefs

class SearchBarOpacityPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = 10
        max = 100
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(XaulinXsSearchBarPrefs.SEARCH_BAR_OPACITY)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(XaulinXsSearchBarPrefs.SEARCH_BAR_OPACITY, newValue as Int)
            true
        }
    }
}
