/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * O AOSP puro já implementa ícones temáticos (monocromáticos, tingidos pela
 * cor do wallpaper) em ThemeManager, mas o toggle de usuário normalmente vive
 * na tela de configurações do módulo Quickstep (Pixel Launcher), que este
 * projeto não compila. Esta preference expõe o mesmo controle
 * (ThemeManager.isMonoThemeEnabled) diretamente na tela de Settings do
 * Launcher3 "puro", sem alterar nenhum arquivo original do AOSP.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.graphics.ThemeManager

class ThemedIconsPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = ThemeManager.INSTANCE.get(context).isMonoThemeEnabled
        setOnPreferenceChangeListener { _, newValue ->
            ThemeManager.INSTANCE.get(context).isMonoThemeEnabled = newValue as Boolean
            true
        }
    }
}
