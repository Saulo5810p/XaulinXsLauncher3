/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Estende a fonte customizada (TTF/OTF importada pelo usuário) para o
 * lado Compose do app — hoje, o Widget Picker (modules/widgetpicker +
 * deferred-appfunctions-widgetpicker), que usa MaterialTheme sem
 * typography customizado (herda FontFamily.Default do Material 3).
 *
 * O View System (Workspace, AllApps, Settings) já é coberto por
 * XaulinXsGlobalFontInflaterFactory, que intercepta o LayoutInflater.
 * Compose não passa por LayoutInflater — TextStyle é resolvido pela
 * árvore de composição, então a única forma de alcançar todo texto
 * Compose de uma vez é sobrescrever o Typography fornecido no
 * MaterialTheme raiz (ver LauncherWidgetPickerTheme.kt).
 */
package com.xaulinxs.customizations.font

import androidx.compose.material3.Typography
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import com.android.launcher3.widgetpicker.ui.theme.WidgetPickerTextStyles
import java.io.File

object XaulinXsComposeFont {

    /**
     * Constrói uma [FontFamily] Compose a partir do arquivo de fonte
     * customizada atualmente configurado, ou retorna null se não houver
     * nenhuma (nesse caso o chamador deve manter o Typography padrão
     * inalterado). Diferente de XaulinXsCustomFont.loadTypefaceIfAvailable
     * (que retorna um android.graphics.Typeface para uso em View System),
     * este método lê o mesmo path salvo mas monta o tipo específico do
     * Compose — Font(file = ...) aceita um java.io.File diretamente,
     * então não precisamos duplicar a lógica de leitura do arquivo, só a
     * de construção do tipo final.
     */
    @Composable
    fun rememberCustomFontFamily(): FontFamily? {
        val context = LocalContext.current
        val path = XaulinXsCustomFont.getCustomFontPath(context)
        return remember(path) {
            buildFontFamilyOrNull(path)
        }
    }

    private fun buildFontFamilyOrNull(path: String?): FontFamily? {
        if (path == null) return null
        val file = File(path)
        if (!file.isFile) return null
        return try {
            FontFamily(Font(file))
        } catch (e: Exception) {
            null
        }
    }

    /**
     * Retorna uma cópia de [base] com [fontFamily] aplicado a todos os 15
     * TextStyle nomeados do Material 3 Typography. Se [fontFamily] for
     * null (nenhuma fonte customizada configurada), retorna [base]
     * inalterado — mantém 100% do comportamento original do Material 3
     * (FontFamily.Default) quando o usuário não importou nenhuma fonte.
     */
    fun applyFontFamily(base: Typography, fontFamily: FontFamily?): Typography {
        if (fontFamily == null) return base
        return Typography(
            displayLarge = base.displayLarge.copy(fontFamily = fontFamily),
            displayMedium = base.displayMedium.copy(fontFamily = fontFamily),
            displaySmall = base.displaySmall.copy(fontFamily = fontFamily),
            headlineLarge = base.headlineLarge.copy(fontFamily = fontFamily),
            headlineMedium = base.headlineMedium.copy(fontFamily = fontFamily),
            headlineSmall = base.headlineSmall.copy(fontFamily = fontFamily),
            titleLarge = base.titleLarge.copy(fontFamily = fontFamily),
            titleMedium = base.titleMedium.copy(fontFamily = fontFamily),
            titleSmall = base.titleSmall.copy(fontFamily = fontFamily),
            bodyLarge = base.bodyLarge.copy(fontFamily = fontFamily),
            bodyMedium = base.bodyMedium.copy(fontFamily = fontFamily),
            bodySmall = base.bodySmall.copy(fontFamily = fontFamily),
            labelLarge = base.labelLarge.copy(fontFamily = fontFamily),
            labelMedium = base.labelMedium.copy(fontFamily = fontFamily),
            labelSmall = base.labelSmall.copy(fontFamily = fontFamily),
        )
    }

    /**
     * Mesmo princípio de [applyFontFamily], mas para
     * [WidgetPickerTextStyles] — os TextStyle específicos do widget
     * picker que vêm de res/values/styles.xml via textStyleFromResource
     * (ver LauncherWidgetPickerTypography.kt), não do Typography do
     * Material 3. Sem isso, aplicar a fonte só no MaterialTheme não
     * bastaria: os textos do widget picker leem
     * WidgetPickerTheme.typography.* diretamente, não
     * MaterialTheme.typography.*.
     */
    fun applyFontFamily(
        base: WidgetPickerTextStyles,
        fontFamily: FontFamily?,
    ): WidgetPickerTextStyles {
        if (fontFamily == null) return base
        return WidgetPickerTextStyles(
            sheetTitle = base.sheetTitle.copy(fontFamily = fontFamily),
            sheetDescription = base.sheetDescription.copy(fontFamily = fontFamily),
            expandableListHeaderTitle =
                base.expandableListHeaderTitle.copy(fontFamily = fontFamily),
            expandableListHeaderSubTitle =
                base.expandableListHeaderSubTitle.copy(fontFamily = fontFamily),
            selectedListHeaderTitle = base.selectedListHeaderTitle.copy(fontFamily = fontFamily),
            unSelectedListHeaderTitle =
                base.unSelectedListHeaderTitle.copy(fontFamily = fontFamily),
            selectedListHeaderSubTitle =
                base.selectedListHeaderSubTitle.copy(fontFamily = fontFamily),
            unSelectedListHeaderSubTitle =
                base.unSelectedListHeaderSubTitle.copy(fontFamily = fontFamily),
            noWidgetsErrorText = base.noWidgetsErrorText.copy(fontFamily = fontFamily),
            widgetLabel = base.widgetLabel.copy(fontFamily = fontFamily),
            widgetSpanText = base.widgetSpanText.copy(fontFamily = fontFamily),
            widgetDescription = base.widgetDescription.copy(fontFamily = fontFamily),
            addWidgetButtonLabel = base.addWidgetButtonLabel.copy(fontFamily = fontFamily),
            toolbarUnSelectedTabLabel =
                base.toolbarUnSelectedTabLabel.copy(fontFamily = fontFamily),
            toolbarSelectedTabLabel =
                base.toolbarSelectedTabLabel.copy(fontFamily = fontFamily),
            searchBarPlaceholderText =
                base.searchBarPlaceholderText.copy(fontFamily = fontFamily),
            searchBarText = base.searchBarText.copy(fontFamily = fontFamily),
        )
    }
}