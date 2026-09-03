/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Calcula a cor de véu ("vidro fosco") usada atrás do App Drawer, a partir
 * da cor extraída do wallpaper via WallpaperColorHints. O alpha parcial é
 * essencial: é o que permite o RenderEffect de blur (ver
 * XaulinXsDepthController) aparecer através do véu, criando o efeito de
 * vidro fosco em vez de esconder tudo atrás de uma cor sólida.
 *
 * getScrimColorIfEnabled() é chamado diretamente por AllAppsState.java
 * (AOSP), que é a origem "de verdade" da cor do scrim consumida pela
 * animação de transição de estado.
 */
package com.xaulinxs.customizations.theme

import android.content.Context
import androidx.core.graphics.ColorUtils
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.Utilities
import com.android.launcher3.util.WallpaperColorHints
import com.xaulinxs.customizations.settings.ThemedScrimPreference.Companion.THEMED_SCRIM_ENABLED
import com.xaulinxs.customizations.theme.XaulinXsManualColor
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

private const val SCRIM_ALPHA_LIGHT = 140
private const val SCRIM_ALPHA_DARK = 160
private const val SHADE_RATIO_LIGHT = 0.15f
private const val SHADE_RATIO_DARK = 0.55f

// XaulinXs Customizations: percentual de opacidade do véu escolhido pelo
// usuário no slider "Transparência do fundo do menu de apps". 100%
// preserva o alpha original (SCRIM_ALPHA_LIGHT/DARK acima); 0% deixa o véu
// totalmente transparente (só o blur real do XaulinXsDepthController fica visível).
const val SCRIM_OPACITY_MIN_PERCENT = 0
const val SCRIM_OPACITY_MAX_PERCENT = 100
private const val KEY_SCRIM_OPACITY_PERCENT = "xaulinxs_scrim_opacity_percent"
val SCRIM_OPACITY_PERCENT = backedUpItem(KEY_SCRIM_OPACITY_PERCENT, SCRIM_OPACITY_MAX_PERCENT)

// XaulinXs Customizations: NOVA transparência do menu de apps (agosto/2026),
// feature separada de SCRIM_OPACITY_PERCENT acima. A diferença é a condição
// de ativação: SCRIM_OPACITY_PERCENT só tem efeito quando o blur do drawer
// (THEMED_SCRIM_ENABLED) está LIGADO — ver getScrimColorIfEnabled() abaixo,
// que corta com "return null" se o blur estiver desligado. Essa nova
// feature faz o oposto por pedido explícito do usuário: só tem efeito
// quando o blur está DESLIGADO, revelando a Workspace por trás do drawer
// sem nenhum desfoque. 0% no slider = totalmente transparente (workspace
// 100% visível); 100% = opaco.
const val ALLAPPS_TRANSPARENCY_MIN_PERCENT = 0
const val ALLAPPS_TRANSPARENCY_MAX_PERCENT = 100
private const val KEY_ALLAPPS_TRANSPARENCY_ENABLED = "xaulinxs_allapps_transparency_enabled"
private const val KEY_ALLAPPS_TRANSPARENCY_PERCENT = "xaulinxs_allapps_transparency_percent"
val ALLAPPS_TRANSPARENCY_ENABLED = backedUpItem(KEY_ALLAPPS_TRANSPARENCY_ENABLED, false)
val ALLAPPS_TRANSPARENCY_PERCENT =
    backedUpItem(KEY_ALLAPPS_TRANSPARENCY_PERCENT, ALLAPPS_TRANSPARENCY_MAX_PERCENT)

object WallpaperScrimHelper {

    @JvmStatic
    fun getScrimColorIfEnabled(context: Context): Int? {
        val prefs = LauncherPrefs.get(context)
        if (prefs.get(THEMED_SCRIM_ENABLED)) return getScrimColor(context)
        // Blur desligado: se a nova transparência estiver ativada, ela
        // assume o fundo do drawer no lugar do véu temático do wallpaper —
        // cor sólida de fundo do tema, com alpha controlado pelo slider,
        // sem nenhum desfoque envolvido.
        if (prefs.get(ALLAPPS_TRANSPARENCY_ENABLED)) return getPlainTransparentScrimColor(context)
        return null
    }

    fun getScrimColor(context: Context): Int? {
        // XaulinXs Customizations: cor manual (se ativada) tem prioridade sobre a do wallpaper.
        val primaryColor = XaulinXsManualColor.getBaseColorIfEnabled(context)
            ?: WallpaperColorHints.get(context).colors?.primaryColor?.toArgb()
            ?: return null
        val isDark = Utilities.isDarkTheme(context)
        val shaded =
            if (isDark) {
                ColorUtils.blendARGB(primaryColor, android.graphics.Color.BLACK, SHADE_RATIO_DARK)
            } else {
                ColorUtils.blendARGB(primaryColor, android.graphics.Color.WHITE, SHADE_RATIO_LIGHT)
            }
        val baseAlpha = if (isDark) SCRIM_ALPHA_DARK else SCRIM_ALPHA_LIGHT
        // XaulinXs Customizations: escala o alpha base pelo percentual do slider.
        val opacityPercent = LauncherPrefs.get(context).get(SCRIM_OPACITY_PERCENT)
            .coerceIn(SCRIM_OPACITY_MIN_PERCENT, SCRIM_OPACITY_MAX_PERCENT)
        val alpha = (baseAlpha * opacityPercent / 100).coerceIn(0, 255)
        return ColorUtils.setAlphaComponent(shaded, alpha)
    }

    /**
     * Cor de fundo "lisa" (sem blur) para a nova transparência do menu de
     * apps: reaproveita a cor de fundo padrão do tema do sistema (mesma
     * usada pelo AOSP original em getWorkspaceScrimColor quando nenhuma
     * customização está ativa) e só ajusta o alpha pelo percentual do
     * slider — nada de tonalidade extraída do wallpaper nem shading, para
     * não ser confundida com o véu temático de SCRIM_OPACITY_PERCENT.
     */
    private fun getPlainTransparentScrimColor(context: Context): Int {
        val baseColor = com.android.launcher3.util.Themes.getAttrColor(
            context, com.android.launcher3.R.attr.allAppsScrimColor
        )
        val percent = LauncherPrefs.get(context).get(ALLAPPS_TRANSPARENCY_PERCENT)
            .coerceIn(ALLAPPS_TRANSPARENCY_MIN_PERCENT, ALLAPPS_TRANSPARENCY_MAX_PERCENT)
        val baseAlpha = android.graphics.Color.alpha(baseColor)
        val alpha = (baseAlpha * percent / 100).coerceIn(0, 255)
        return ColorUtils.setAlphaComponent(baseColor, alpha)
    }
}

// XAULINXS_ALLAPPS_TRANSPARENCY_V2_FILE
