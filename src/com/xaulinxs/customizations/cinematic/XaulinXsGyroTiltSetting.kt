/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Interruptor liga/desliga do tilt por giroscópio (GyroTiltProvider +
 * uso em CinematicCoverFlowEffect). Segue o mesmo padrão de preferência
 * "backed up" já usado por POPUP_BLUR_ENABLED/THEMED_SCRIM_ENABLED.
 */
package com.xaulinxs.customizations.cinematic

import android.content.Context
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

object XaulinXsGyroTiltSetting {
    private const val KEY_ENABLED = "xaulinxs_gyro_tilt_enabled"

    @JvmField
    val GYRO_TILT_ENABLED = backedUpItem(KEY_ENABLED, true)

    @JvmStatic
    fun isEnabled(context: Context): Boolean =
        LauncherPrefs.get(context).get(GYRO_TILT_ENABLED)
}

// XAULINXS_GYRO_TILT_SETTING_FILE
