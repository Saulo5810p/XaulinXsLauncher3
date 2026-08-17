/*
 * Copyright (C) 2025 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.android.launcher3.widgetpicker.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import com.android.launcher3.widgetpicker.ui.theme.WidgetPickerTheme
import com.xaulinxs.customizations.font.XaulinXsComposeFont

/** Contains theme that launcher applies to the widget picker. */
@Composable
fun LauncherWidgetPickerTheme(
    supportsBlurTokens: Boolean = false,
    isBlurEnabled: Boolean = false,
    content: @Composable () -> Unit,
) {
    val widgetPickerColors =
        if (isSystemInDarkTheme()) {
            darkWidgetPickerColors(
                supportsBlurTokens = supportsBlurTokens,
                isBlurEnabled = isBlurEnabled,
            )
        } else {
            lightWidgetPickerColors(
                supportsBlurTokens = supportsBlurTokens,
                isBlurEnabled = isBlurEnabled,
            )
        }

    // XaulinXs Customizations: estende a fonte customizada (TTF/OTF
    // importada pelo usuário) para o Widget Picker Compose. Sem isso,
    // MaterialTheme() usa FontFamily.Default do Material 3 e
    // launcherWidgetPickerTextStyles() lê fontFamily dos estilos XML via
    // DeviceFontFamilyName, que só resolve fontes de sistema — nenhum
    // dos dois caminhos suporta um arquivo de fonte arbitrário. Quando
    // não há fonte customizada configurada (rememberCustomFontFamily
    // retorna null), applyFontFamily devolve o typography/textStyles
    // originais sem qualquer alteração — comportamento 100% original
    // preservado nesse caso.
    val xaulinxsFontFamily = XaulinXsComposeFont.rememberCustomFontFamily()
    val baseTextStyles = launcherWidgetPickerTextStyles()
    val widgetPickerTextStyles =
        XaulinXsComposeFont.applyFontFamily(baseTextStyles, xaulinxsFontFamily)

    MaterialTheme(
        typography = XaulinXsComposeFont.applyFontFamily(
            MaterialTheme.typography, xaulinxsFontFamily),
    ) {
        WidgetPickerTheme(
            colors = widgetPickerColors,
            textStyles = widgetPickerTextStyles,
        ) {
            content()
        }
    }
}
