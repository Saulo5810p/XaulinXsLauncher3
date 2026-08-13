/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Ponto único que Hotseat.java consulta para decidir se usa nossa barra
 * de busca própria ou o QSB original do AOSP. Retornar null preserva
 * 100% do comportamento padrão.
 */
package com.xaulinxs.customizations.search

import android.content.Context
import android.view.View
import android.view.ViewGroup
import com.android.launcher3.LauncherPrefs

object XaulinXsSearchBarFactory {
    @JvmStatic
    fun createViewIfEnabled(context: Context, container: ViewGroup): View? {
        if (!LauncherPrefs.get(context).get(XaulinXsSearchBarPrefs.SEARCH_BAR_ENABLED)) return null
        return XaulinXsSearchBarView(context)
    }
}
