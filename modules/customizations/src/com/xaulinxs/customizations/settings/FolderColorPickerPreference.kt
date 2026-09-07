/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.Preference
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.R
import com.xaulinxs.customizations.folder.XaulinXsFolderAppearance

class FolderColorPickerPreference
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
            titleRes = R.string.xaulinxs_folder_color_picker_title,
            currentColor = prefs.get(XaulinXsFolderAppearance.FOLDER_COLOR_ARGB),
        ) { newColor ->
            prefs.put(XaulinXsFolderAppearance.FOLDER_COLOR_ARGB, newColor)
            updateSummary()
        }
    }

    private fun updateSummary() {
        val color = LauncherPrefs.get(context).get(XaulinXsFolderAppearance.FOLDER_COLOR_ARGB)
        summary = String.format("#%06X", 0xFFFFFF and color)
    }
}
