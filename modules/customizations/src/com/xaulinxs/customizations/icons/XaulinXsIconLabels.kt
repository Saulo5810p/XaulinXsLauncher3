/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Guarda e lê o toggle de "ocultar labels dos ícones". Lido diretamente por
 * BubbleTextView.applyLabel() (edição cirúrgica em BubbleTextView.java) —
 * funciona pra qualquer BubbleTextView (home, hotseat, pasta, app drawer),
 * já que é o ponto único onde todo label de ícone é setado no AOSP.
 *
 * Não reaproveita LauncherPrefs.WORKSPACE_ITEMS_LABEL_HIDDEN (mecanismo
 * nativo do AOSP) de propósito: esse mecanismo só funciona no grid
 * responsivo, que este device não usa (ver comentário no topo do script
 * feature_icon_labels.py).
 */
package com.xaulinxs.customizations.icons

import android.content.Context
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

object XaulinXsIconLabels {
    private const val KEY_LABELS_HIDDEN = "xaulinxs_icon_labels_hidden"

    @JvmField
    val LABELS_HIDDEN = backedUpItem(KEY_LABELS_HIDDEN, false)

    @JvmStatic
    fun isHidden(context: Context): Boolean = LauncherPrefs.get(context).get(LABELS_HIDDEN)
}
