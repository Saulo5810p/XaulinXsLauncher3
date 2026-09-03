/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.cinematic.GyroTiltProvider
import com.xaulinxs.customizations.cinematic.XaulinXsGyroTiltSetting.GYRO_TILT_ENABLED

class GyroTiltPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(GYRO_TILT_ENABLED)
        setOnPreferenceChangeListener { _, newValue ->
            val enabled = newValue as Boolean
            LauncherPrefs.get(context).put(GYRO_TILT_ENABLED, enabled)
            GyroTiltProvider.notifySettingChanged(context, enabled)
            true
        }
    }
}

// XAULINXS_GYRO_TILT_PREFERENCE_FILE
