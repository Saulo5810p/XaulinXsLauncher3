/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Feature nova (info.txt/etapa 3): "remover fundo/sombra dos ícones" —
 * apps antigos que não enviam um ícone adaptativo (<adaptive-icon> com
 * layer de background própria) recebem, hoje, um retângulo BRANCO sólido
 * sintético (BaseIconFactory.wrapToAdaptiveIcon -> DEFAULT_WRAPPER_BACKGROUND
 * = Color.WHITE) mais uma sombra desenhada acompanhando essa máscara
 * (BaseIconFactory.drawableToBitmap -> shadowGenerator.addPathShadow). É
 * esse combo (fundo branco + sombra) que fica feio atrás de ícones antigos
 * quadrados/com fundo transparente.
 *
 * Ícones adaptativos de verdade (a maioria dos apps atualizados) NÃO usam
 * esse wrapper — já têm a própria layer de background — então esta opção
 * não altera a aparência deles, só a dos ícones legados encapsulados.
 */
package com.xaulinxs.customizations.icons

import android.content.Context
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

object XaulinXsLegacyIconAppearance {

    private const val KEY_REMOVE_LEGACY_BG_SHADOW = "xaulinxs_legacy_icon_bg_shadow_removed"
    val LEGACY_ICON_BG_SHADOW_REMOVED = backedUpItem(KEY_REMOVE_LEGACY_BG_SHADOW, false)

    @JvmStatic
    fun shouldRemoveBackgroundAndShadow(context: Context): Boolean =
        LauncherPrefs.get(context).get(LEGACY_ICON_BG_SHADOW_REMOVED)
}
