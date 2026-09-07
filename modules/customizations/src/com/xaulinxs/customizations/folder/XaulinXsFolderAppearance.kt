/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Feature nova (info.txt/etapa 3): "Pastas - Cor customizada - 3 sliders +
 * editor hex + paleta; Transparência com slider 0-100; Tamanho da pasta -
 * slider 0-100."
 *
 * Todas as três, desligadas/neutras por padrão (cor customizada off = usa
 * a cor de tema padrão do AOSP; transparência 100% = opaco, sem mudança;
 * tamanho 100% = tamanho padrão do AOSP) — só mudam o visual se o usuário
 * mexer explicitamente, mesmo padrão das outras features de aparência já
 * construídas neste projeto (ex.: cor manual, cor dos balões).
 */
package com.xaulinxs.customizations.folder

import android.content.Context
import android.graphics.Color
import androidx.core.graphics.ColorUtils
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

private const val KEY_FOLDER_COLOR_ENABLED = "xaulinxs_folder_color_enabled"
private const val KEY_FOLDER_COLOR_ARGB = "xaulinxs_folder_color_argb"
private const val KEY_FOLDER_TRANSPARENCY_PERCENT = "xaulinxs_folder_transparency_percent"
private const val KEY_FOLDER_SIZE_PERCENT = "xaulinxs_folder_size_percent"

// Tamanho mínimo permitido (%) — abaixo disso a pasta fica pequena demais
// pra ser tocada de forma confiável (alvo de toque mínimo recomendável).
private const val MIN_FOLDER_SIZE_PERCENT = 30

object XaulinXsFolderAppearance {

    const val TRANSPARENCY_MIN_PERCENT = 0
    const val TRANSPARENCY_MAX_PERCENT = 100
    const val SIZE_MIN_PERCENT = MIN_FOLDER_SIZE_PERCENT
    const val SIZE_MAX_PERCENT = 100

    val FOLDER_COLOR_ENABLED = backedUpItem(KEY_FOLDER_COLOR_ENABLED, false)
    val FOLDER_COLOR_ARGB = backedUpItem(KEY_FOLDER_COLOR_ARGB, Color.WHITE)
    val FOLDER_TRANSPARENCY_PERCENT =
        backedUpItem(KEY_FOLDER_TRANSPARENCY_PERCENT, TRANSPARENCY_MAX_PERCENT)
    val FOLDER_SIZE_PERCENT = backedUpItem(KEY_FOLDER_SIZE_PERCENT, SIZE_MAX_PERCENT)

    /**
     * Cor de fundo da pasta já com a transparência do slider aplicada.
     * [baseColor] é a cor original resolvida pelo AOSP (PreviewBackground.mBgColor,
     * vinda do tema) — usada como está quando a cor customizada está
     * desligada.
     */
    @JvmStatic
    fun resolveBackgroundColor(context: Context, baseColor: Int): Int {
        val prefs = LauncherPrefs.get(context)
        val color = if (prefs.get(FOLDER_COLOR_ENABLED)) prefs.get(FOLDER_COLOR_ARGB) else baseColor
        val percent = prefs.get(FOLDER_TRANSPARENCY_PERCENT)
            .coerceIn(TRANSPARENCY_MIN_PERCENT, TRANSPARENCY_MAX_PERCENT)
        val baseAlpha = Color.alpha(color)
        val alpha = (baseAlpha * percent / 100).coerceIn(0, 255)
        return ColorUtils.setAlphaComponent(color, alpha)
    }

    /** [defaultSizePx] é o tamanho calculado normalmente pelo AOSP (DeviceProfile). */
    @JvmStatic
    fun resolvePreviewSizePx(context: Context, defaultSizePx: Int): Int {
        val percent = LauncherPrefs.get(context).get(FOLDER_SIZE_PERCENT)
            .coerceIn(SIZE_MIN_PERCENT, SIZE_MAX_PERCENT)
        return defaultSizePx * percent / 100
    }
}
