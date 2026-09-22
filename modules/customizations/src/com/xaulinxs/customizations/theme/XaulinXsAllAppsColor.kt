/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Cor manual do fundo do Menu de aplicativo (categoria "Menu de
 * aplicativo" das Settings), com paleta + sliders RGB + editor hex —
 * pedido explícito do usuário, distinto de XaulinXsManualColor (que
 * afeta ícones temáticos + o véu com blur ligado) e de
 * XaulinXsBalloonColor (balões/menus de contexto). Mesmo padrão
 * estrutural dessas duas: um par ENABLED/ARGB via
 * LauncherPrefs.backedUpItem().
 *
 * Condição de ativação pedida pelo usuário: só tem efeito quando o
 * "Fundo desfocado no menu de apps" (ThemedScrimPreference /
 * THEMED_SCRIM_ENABLED) estiver DESATIVADO — mesma condição que já
 * rege ALLAPPS_TRANSPARENCY_ENABLED em WallpaperScrimHelper.kt. Quando
 * o blur está ligado, esta cor é ignorada e o fundo continua sendo o
 * mBottomSheetBackgroundColorOverBlur normal do AOSP.
 *
 * A transparência do menu de apps (ALLAPPS_TRANSPARENCY_PERCENT) já é
 * aplicada por cima de qualquer baseColor em applyAllAppsTransparency()
 * — pedido do usuário ("fazer com que a feature de Transparência se
 * aplique a ele também") já cai de graça: getColorOverrideIfEnabled()
 * só precisa substituir o baseColor de entrada, quem aplica o alpha do
 * slider continua sendo a mesma função de sempre.
 */
package com.xaulinxs.customizations.theme

import android.content.Context
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem
import com.xaulinxs.customizations.settings.ThemedScrimPreference.Companion.THEMED_SCRIM_ENABLED

private const val KEY_ALLAPPS_COLOR_ENABLED = "xaulinxs_allapps_color_enabled"
private const val KEY_ALLAPPS_COLOR_ARGB = "xaulinxs_allapps_color_argb"

// Mesmo roxo Material usado como default nos outros color pickers do
// projeto (QsbConfig.DEFAULT_BAR_COLOR, XaulinXsManualColor.DEFAULT_COLOR),
// por consistência visual entre as telas de personalização.
private const val DEFAULT_ALLAPPS_COLOR = 0xFF6750A4.toInt()

object XaulinXsAllAppsColor {

    val ALLAPPS_COLOR_ENABLED = backedUpItem(KEY_ALLAPPS_COLOR_ENABLED, false)
    val ALLAPPS_COLOR_ARGB = backedUpItem(KEY_ALLAPPS_COLOR_ARGB, DEFAULT_ALLAPPS_COLOR)

    /**
     * Cor manual (ARGB opaco) para o fundo do menu de apps, ou null se a
     * feature não deve se aplicar agora — seja porque está desligada,
     * seja porque o fundo desfocado está ativo (condição exigida pelo
     * usuário). Nesse caso o chamador deve usar o baseColor original.
     */
    @JvmStatic
    fun getColorOverrideIfEnabled(context: Context): Int? {
        val prefs = LauncherPrefs.get(context)
        if (prefs.get(THEMED_SCRIM_ENABLED)) return null
        if (!prefs.get(ALLAPPS_COLOR_ENABLED)) return null
        return prefs.get(ALLAPPS_COLOR_ARGB)
    }
}

// XAULINXS_ALLAPPS_COLOR_DATA_FILE
