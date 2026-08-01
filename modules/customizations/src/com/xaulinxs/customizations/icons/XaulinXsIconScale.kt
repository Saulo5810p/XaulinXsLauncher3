/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Guarda e valida o percentual de escala de ícone (100%-200%) escolhido pelo
 * usuário. Lido por InvariantDeviceProfile.applyXaulinXsIconScaleOverride()
 * (edição cirúrgica em InvariantDeviceProfile.java) e escrito pela
 * com.xaulinxs.customizations.settings.IconScalePreference.
 */
package com.xaulinxs.customizations.icons

import android.content.Context
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

object XaulinXsIconScale {
    private const val KEY_ICON_SCALE_PERCENT = "xaulinxs_icon_scale_percent"
    const val MIN_PERCENT = 100
    const val MAX_PERCENT = 200

    @JvmField
    val ICON_SCALE_PERCENT = backedUpItem(KEY_ICON_SCALE_PERCENT, MIN_PERCENT)

    @JvmStatic
    fun getScalePercent(context: Context): Int {
        val stored = LauncherPrefs.get(context).get(ICON_SCALE_PERCENT)
        return stored.coerceIn(MIN_PERCENT, MAX_PERCENT)
    }
}
