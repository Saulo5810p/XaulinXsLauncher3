/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.theme.SCRIM_OPACITY_MAX_PERCENT
import com.xaulinxs.customizations.theme.SCRIM_OPACITY_MIN_PERCENT
import com.xaulinxs.customizations.theme.SCRIM_OPACITY_PERCENT

class ScrimOpacityPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = SCRIM_OPACITY_MIN_PERCENT
        max = SCRIM_OPACITY_MAX_PERCENT
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(SCRIM_OPACITY_PERCENT)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(SCRIM_OPACITY_PERCENT, newValue as Int)
            // XaulinXs Customizations: não precisa forçar nada — a cor do véu é
            // recalculada do zero toda vez que o App Drawer abre
            // (AllAppsState.getWorkspaceScrimColor() -> WallpaperScrimHelper.getScrimColor()).
            true
        }
    }
}
