/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Conteúdo da página fixa de música: widget grande de lista em cima e o
 * mini player 4x2 logo abaixo. É inserido num CellLayout do Workspace,
 * ocupando a grade inteira (por isso nada pode ser solto nela).
 */
package com.xaulinxs.customizations.misc.music

import android.content.Context
import android.view.ViewGroup
import android.widget.LinearLayout
import com.android.launcher3.LauncherSettings
import com.android.launcher3.model.data.ItemInfo
import com.xaulinxs.customizations.misc.XaulinXsMiscSettings

class XaulinXsMusicPageView(context: Context) : LinearLayout(context) {

    init {
        orientation = VERTICAL
        val gap = (8 * resources.displayMetrics.density).toInt()
        super.setPadding(gap, gap, gap, gap)

        addView(XaulinXsMusicListWidget(context), LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        val mini = XaulinXsMiniPlayerWidget(context)
        addView(
            mini,
            LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, (150 * resources.displayMetrics.density).toInt())
                .apply { topMargin = gap },
        )

        // Alguns operadores do Workspace (mapOverItems) fazem cast de getTag() para ItemInfo
        // sem checar null; esta etiqueta "não acionável" evita NPE. Nunca é gravada no banco.
        tag = ItemInfo().apply {
            itemType = LauncherSettings.Favorites.ITEM_TYPE_NON_ACTIONABLE
            container = LauncherSettings.Favorites.CONTAINER_DESKTOP
            screenId = XaulinXsMiscSettings.MUSIC_SCREEN_ID
        }
        setOnLongClickListener { true }
    }

    // CellLayout.measureChild() aplica padding de ícone em qualquer filho; ignoramos.
    override fun setPadding(left: Int, top: Int, right: Int, bottom: Int) = Unit
}
