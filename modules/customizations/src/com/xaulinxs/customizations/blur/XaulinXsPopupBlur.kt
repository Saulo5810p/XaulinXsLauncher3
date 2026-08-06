/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.blur

import android.content.Context
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

object XaulinXsPopupBlur {
    private const val KEY_ENABLED = "xaulinxs_popup_blur_enabled"

    @JvmField
    val POPUP_BLUR_ENABLED = backedUpItem(KEY_ENABLED, true)

    @JvmStatic
    fun isEnabled(context: Context): Boolean = LauncherPrefs.get(context).get(POPUP_BLUR_ENABLED)
}
