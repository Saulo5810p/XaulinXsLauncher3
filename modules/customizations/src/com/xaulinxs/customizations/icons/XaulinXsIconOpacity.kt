/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Guarda e lê a opacidade dos ícones (0%-100%, 100% = opaco, igual ao
 * comportamento original). Lido diretamente por
 * BubbleTextView.applyCompoundDrawables() (edição cirúrgica em
 * BubbleTextView.java) — funciona pra qualquer BubbleTextView (home,
 * hotseat, pasta, app drawer), já que é o ponto único onde todo ícone é
 * aplicado no AOSP.
 */
package com.xaulinxs.customizations.icons

import android.content.Context
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

object XaulinXsIconOpacity {
    private const val KEY_ICON_OPACITY_PERCENT = "xaulinxs_icon_opacity_percent"
    const val MIN_PERCENT = 0
    const val MAX_PERCENT = 100

    @JvmField
    val ICON_OPACITY_PERCENT = backedUpItem(KEY_ICON_OPACITY_PERCENT, MAX_PERCENT)

    @JvmStatic
    fun getAlpha(context: Context): Int {
        val percent = LauncherPrefs.get(context).get(ICON_OPACITY_PERCENT).coerceIn(MIN_PERCENT, MAX_PERCENT)
        return Math.round(percent * 255f / 100f)
    }
}
