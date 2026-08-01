/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.InvariantDeviceProfile
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.icons.XaulinXsIconScale
import com.xaulinxs.customizations.icons.XaulinXsIconScale.ICON_SCALE_PERCENT

class IconScalePreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = XaulinXsIconScale.MIN_PERCENT
        max = XaulinXsIconScale.MAX_PERCENT
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(ICON_SCALE_PERCENT)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(ICON_SCALE_PERCENT, newValue as Int)
            // XaulinXs Customizations: recalcula o grid/ícone com o novo tamanho
            InvariantDeviceProfile.INSTANCE.get(context).onXaulinXsIconScaleChanged()
            true
        }
    }
}
