/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.folder.XaulinXsFolderAppearance

class FolderTransparencyPreference
@JvmOverloads
constructor(context: Context, attrs: AttributeSet? = null) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = XaulinXsFolderAppearance.TRANSPARENCY_MIN_PERCENT
        max = XaulinXsFolderAppearance.TRANSPARENCY_MAX_PERCENT
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(XaulinXsFolderAppearance.FOLDER_TRANSPARENCY_PERCENT)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context)
                .put(XaulinXsFolderAppearance.FOLDER_TRANSPARENCY_PERCENT, newValue as Int)
            true
        }
    }
}
