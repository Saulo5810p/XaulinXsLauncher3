/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.Preference
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.R
import com.xaulinxs.customizations.theme.XaulinXsBalloonColor

class BalloonColorPickerPreference
@JvmOverloads
constructor(context: Context, attrs: AttributeSet? = null) : Preference(context, attrs) {

    init {
        isPersistent = false
        updateSummary()
    }

    override fun onClick() {
        val prefs = LauncherPrefs.get(context)
        RgbHexColorDialogHelper.show(
            context = context,
            titleRes = R.string.xaulinxs_balloon_color_picker_title,
            currentColor = prefs.get(XaulinXsBalloonColor.BALLOON_COLOR_ARGB),
        ) { newColor ->
            prefs.put(XaulinXsBalloonColor.BALLOON_COLOR_ARGB, newColor)
            updateSummary()
        }
    }

    private fun updateSummary() {
        val color = LauncherPrefs.get(context).get(XaulinXsBalloonColor.BALLOON_COLOR_ARGB)
        summary = String.format("#%06X", 0xFFFFFF and color)
    }
}
