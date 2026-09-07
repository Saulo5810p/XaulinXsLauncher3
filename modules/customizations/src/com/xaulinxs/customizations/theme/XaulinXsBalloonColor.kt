/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Feature nova (info.txt/etapa 3): "Balões do app estão todos em branco.
 * Corrigir para que sigam a cor padrão da cor do papel de parede. A não
 * ser que a feature de cor dos balões [...] esteja desativada [ligada]."
 *
 * CAUSA RAIZ do balão branco: ArrowPopup.java resolve sua cor de fundo via
 * dois caminhos, ambos dependentes do sistema de "dynamic color" (Monet)
 * do próprio Android:
 *  - R.attr.popupColorPrimary -> res/values/colors.xml (fallback pré-API 31)
 *    define popup_color_primary_light = #FFF (branco sólido, literal);
 *    só em res/values-v31/colors.xml isso vira
 *    @android:color/system_accent2_50 (cor real do Monet).
 *  - R.color.materialColorSurfaceContainer -> mesma história em
 *    material_dynamic_colors_fallback.xml (#F3EDF7, quase branco).
 * Este projeto já tem HISTÓRICO de o Monet/dynamic-color do sistema não
 * funcionar neste device (mesmo motivo documentado em
 * XaulinXsMonoIconThemeFactory e XaulinXsThemedIconColors, que por isso
 * também pararam de depender de recursos estáticos e passaram a extrair a
 * cor do wallpaper na mão via WallpaperColorHints). Os balões nunca
 * receberam o mesmo tratamento — por isso ficam brancos.
 *
 * Fix: por padrão, os balões passam a usar a MESMA cor extraída do
 * wallpaper que o resto do launcher já usa (WallpaperColorHints), com um
 * leve blend pra claro/escuro igual ao já usado em WallpaperScrimHelper —
 * mas em opacidade total (255), já que aqui é o fundo sólido de um menu,
 * não um véu translúcido. Se a extração falhar por qualquer motivo (sem
 * WallpaperColorHints disponível), cai de volta pro comportamento AOSP
 * original (mColors do ArrowPopup), sem quebrar nada.
 *
 * BALLOON_COLOR_ENABLED + BALLOON_COLOR_ARGB já deixam pronta a estrutura
 * pra a feature futura de cor customizada dos balões (3 sliders + paleta +
 * editor hex) mencionada no info.txt — quando ligada, ela tem prioridade
 * sobre a cor extraída do wallpaper, do mesmo jeito que XaulinXsManualColor
 * já tem prioridade sobre a cor de ícones/scrim.
 */
package com.xaulinxs.customizations.theme

import android.content.Context
import android.graphics.Color
import androidx.core.graphics.ColorUtils
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem
import com.android.launcher3.Utilities
import com.android.launcher3.util.WallpaperColorHints

private const val KEY_BALLOON_COLOR_ENABLED = "xaulinxs_balloon_color_enabled"
private const val KEY_BALLOON_COLOR_ARGB = "xaulinxs_balloon_color_argb"
private const val SHADE_RATIO_LIGHT = 0.90f
private const val SHADE_RATIO_DARK = 0.80f

object XaulinXsBalloonColor {

    val BALLOON_COLOR_ENABLED = backedUpItem(KEY_BALLOON_COLOR_ENABLED, false)
    val BALLOON_COLOR_ARGB = backedUpItem(KEY_BALLOON_COLOR_ARGB, Color.WHITE)

    /**
     * Cor de fundo pra usar nos balões (menus de contexto), ou null se
     * nenhuma customização se aplica — nesse caso o chamador deve cair de
     * volta pro comportamento AOSP original.
     */
    @JvmStatic
    fun getBalloonColorOverride(context: Context): Int? {
        val prefs = LauncherPrefs.get(context)
        if (prefs.get(BALLOON_COLOR_ENABLED)) return prefs.get(BALLOON_COLOR_ARGB)

        val primary = WallpaperColorHints.get(context).colors?.primaryColor?.toArgb() ?: return null
        val isDark = Utilities.isDarkTheme(context)
        return if (isDark) {
            ColorUtils.blendARGB(primary, Color.BLACK, SHADE_RATIO_DARK)
        } else {
            ColorUtils.blendARGB(primary, Color.WHITE, SHADE_RATIO_LIGHT)
        }
    }
}
