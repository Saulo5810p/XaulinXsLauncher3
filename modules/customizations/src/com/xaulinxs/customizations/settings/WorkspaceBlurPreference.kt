/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.theme.XaulinXsWorkspaceBlur

class WorkspaceBlurPreference
@JvmOverloads
constructor(context: Context, attrs: AttributeSet? = null) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = XaulinXsWorkspaceBlur.MIN_PERCENT
        max = XaulinXsWorkspaceBlur.MAX_PERCENT
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(XaulinXsWorkspaceBlur.WORKSPACE_BLUR_PERCENT)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(XaulinXsWorkspaceBlur.WORKSPACE_BLUR_PERCENT, newValue as Int)
            // XaulinXsWallpaperView escuta essa notificação pra reaplicar o
            // RenderEffect na hora, sem precisar reabrir o launcher.
            XaulinXsWorkspaceBlur.notifyChanged()
            true
        }
    }
}
