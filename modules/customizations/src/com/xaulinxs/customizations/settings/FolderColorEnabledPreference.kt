/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.folder.XaulinXsFolderAppearance

class FolderColorEnabledPreference
@JvmOverloads
constructor(context: Context, attrs: AttributeSet? = null) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(XaulinXsFolderAppearance.FOLDER_COLOR_ENABLED)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(XaulinXsFolderAppearance.FOLDER_COLOR_ENABLED, newValue as Boolean)
            true
        }
    }
}
