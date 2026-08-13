/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Todas as preferences da barra de busca própria (Feature 7).
 */
package com.xaulinxs.customizations.search

import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

object XaulinXsSearchBarPrefs {
    val SEARCH_BAR_ENABLED = backedUpItem("xaulinxs_searchbar_enabled", false)

    // true = modo "busca na web" (ação de busca do teclado dispara
    // ACTION_WEB_SEARCH); false = campo de texto livre, sem ação.
    val SEARCH_BAR_WEB_MODE = backedUpItem("xaulinxs_searchbar_web_mode", true)

    val SEARCH_BAR_OPACITY = backedUpItem("xaulinxs_searchbar_opacity", 70)

    val SEARCH_BAR_CUSTOM_COLOR_ENABLED = backedUpItem("xaulinxs_searchbar_custom_color_enabled", false)
    val SEARCH_BAR_CUSTOM_COLOR_VALUE = backedUpItem("xaulinxs_searchbar_custom_color_value", 0xFF6750A4.toInt())

    val SEARCH_BAR_BLUR_ENABLED = backedUpItem("xaulinxs_searchbar_blur_enabled", false)
}
