/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Categoria Pastas: interruptor + slider 0-200% do desfoque das pastas (mesmos valores dos ícones).
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherAppState
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.folder.XaulinXsFolderBlur

class FolderBlurEnabledPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(XaulinXsFolderBlur.FOLDER_BLUR_ENABLED)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(XaulinXsFolderBlur.FOLDER_BLUR_ENABLED, newValue as Boolean)
            LauncherAppState.getInstance(context).model.forceReload("xaulinxs_folder_blur_toggle")
            true
        }
    }
}

class FolderBlurPercentPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = XaulinXsFolderBlur.MIN_PERCENT
        max = XaulinXsFolderBlur.MAX_PERCENT
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(XaulinXsFolderBlur.FOLDER_BLUR_PERCENT)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(XaulinXsFolderBlur.FOLDER_BLUR_PERCENT, newValue as Int)
            LauncherAppState.getInstance(context).model.forceReload("xaulinxs_folder_blur_percent")
            true
        }
    }
}
