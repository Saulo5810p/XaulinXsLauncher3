/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Storage das configurações da tela dedicada de QSB (Tamanho, Largura,
 * Transparência, Cor da barra, Modo Web/Texto). Mesmo padrão usado por
 * XaulinXsManualColor e XaulinXsCustomFont: LauncherPrefs.backedUpItem()
 * (chave + default, tipo inferido do default), nunca SharedPreferences
 * próprio — assim as configs entram no mesmo mecanismo de backup/restore
 * que o resto do launcher já usa.
 *
 * Modo Web e Modo Texto são mutuamente exclusivos por design: um único
 * boolean (MODE_TEXT_ENABLED) representa os dois estados — não há
 * nenhuma combinação onde ambos ficam ativos ou ambos desativados ao
 * mesmo tempo.
 */
package com.xaulinxs.customizations.qsb

import android.content.Context
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

object QsbConfig {

    // --- Faixas dos 4 sliders ---
    const val MIN_SIZE_PERCENT = 50
    const val MAX_SIZE_PERCENT = 200
    const val DEFAULT_SIZE_PERCENT = 100

    const val MIN_WIDTH_PERCENT = 50
    const val MAX_WIDTH_PERCENT = 100
    const val DEFAULT_WIDTH_PERCENT = 100

    const val MIN_TRANSPARENCY_PERCENT = 0
    const val MAX_TRANSPARENCY_PERCENT = 100
    const val DEFAULT_TRANSPARENCY_PERCENT = 0

    // Mesmo roxo Material usado como default em XaulinXsManualColor, por
    // consistência visual entre as duas telas de personalização.
    private const val DEFAULT_BAR_COLOR = 0xFF6750A4.toInt()

    val SIZE_PERCENT = backedUpItem("xaulinxs_qsb_size_percent", DEFAULT_SIZE_PERCENT)
    val WIDTH_PERCENT = backedUpItem("xaulinxs_qsb_width_percent", DEFAULT_WIDTH_PERCENT)
    val TRANSPARENCY_PERCENT =
        backedUpItem("xaulinxs_qsb_transparency_percent", DEFAULT_TRANSPARENCY_PERCENT)
    val BAR_COLOR = backedUpItem("xaulinxs_qsb_bar_color", DEFAULT_BAR_COLOR)

    /** true = Modo Texto (comandos/campo livre); false = Modo Web (busca/browser, padrão). */
    val MODE_TEXT_ENABLED = backedUpItem("xaulinxs_qsb_mode_text_enabled", false)

    @JvmStatic
    fun getSizePercent(context: Context): Int = LauncherPrefs.get(context).get(SIZE_PERCENT)

    @JvmStatic
    fun getWidthPercent(context: Context): Int = LauncherPrefs.get(context).get(WIDTH_PERCENT)

    @JvmStatic
    fun getTransparencyPercent(context: Context): Int =
        LauncherPrefs.get(context).get(TRANSPARENCY_PERCENT)

    @JvmStatic
    fun getBarColor(context: Context): Int = LauncherPrefs.get(context).get(BAR_COLOR)

    @JvmStatic
    fun isTextModeEnabled(context: Context): Boolean =
        LauncherPrefs.get(context).get(MODE_TEXT_ENABLED)
}
