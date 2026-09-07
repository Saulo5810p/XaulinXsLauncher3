/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.theme.XaulinXsInAppWallpaperSetting
import com.xaulinxs.customizations.theme.XaulinXsInAppWallpaperSetting.IN_APP_WALLPAPER_ENABLED

class InAppWallpaperEnabledPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(IN_APP_WALLPAPER_ENABLED)
        setOnPreferenceChangeListener { _, newValue ->
            val enabled = newValue as Boolean
            LauncherPrefs.get(context).put(IN_APP_WALLPAPER_ENABLED, enabled)
            XaulinXsInAppWallpaperSetting.notifyChanged()
            true
        }
    }
}
