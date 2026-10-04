/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Preferências da categoria "R's Misc": interruptores da página fixa de
 * música (widget de lista + mini player 4x2) e do widget de clima.
 */
package com.xaulinxs.customizations.misc

import android.content.Context
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem
import com.android.launcher3.LauncherPrefs.Companion.nonRestorableItem

object XaulinXsMiscSettings {

    /**
     * Id de "screen" reservado da página de música. É NEGATIVO de propósito:
     * Workspace.canRemoveEmptyScreen() só remove páginas com id > FIRST_SCREEN_ID,
     * então a página nunca é apagada como "página vazia". Não colide com
     * EXTRA_EMPTY_SCREEN_ID (-201) nem EXTRA_EMPTY_SCREEN_SECOND_ID (-200).
     */
    const val MUSIC_SCREEN_ID = -300

    // Ligados por padrão: o pedido é que só dê para desativar pelas configurações.
    @JvmField
    val MUSIC_PAGE_ENABLED = backedUpItem("xaulinxs_music_page_enabled", true)

    @JvmField
    val WEATHER_ENABLED = backedUpItem("xaulinxs_weather_enabled", true)

    // O popup de localização é mostrado automaticamente só uma vez.
    @JvmField
    val LOCATION_PROMPT_SHOWN = nonRestorableItem("xaulinxs_location_prompt_shown", false)

    @JvmStatic
    fun isMusicPageEnabled(context: Context): Boolean =
        LauncherPrefs.get(context).get(MUSIC_PAGE_ENABLED)

    @JvmStatic
    fun isWeatherEnabled(context: Context): Boolean =
        LauncherPrefs.get(context).get(WEATHER_ENABLED)
}
