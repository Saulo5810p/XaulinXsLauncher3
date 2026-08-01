/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * O Widget Picker usa Jetpack Compose Material3, sistema de tema separado
 * do tema de Views tradicional. Sem ColorScheme explícito, MaterialTheme {}
 * usa a paleta roxa padrão da própria biblioteca.
 */
package com.xaulinxs.customizations.theme

import androidx.compose.material3.ColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.ui.graphics.Color

val XaulinXsComposeColorScheme: ColorScheme =
    lightColorScheme(
        primary = Color(0xFFA12668),
        onPrimary = Color(0xFFFFFFFF),
        primaryContainer = Color(0xFFF1D0E2),
        onPrimaryContainer = Color(0xFF3B0C25),
        secondary = Color(0xFF8B4B6D),
        onSecondary = Color(0xFFFFFFFF),
        secondaryContainer = Color(0xFFE6CBDA),
        onSecondaryContainer = Color(0xFF67324E),
        tertiary = Color(0xFFA63F76),
        onTertiary = Color(0xFFFFFFFF),
        tertiaryContainer = Color(0xFFE8C9DA),
        onTertiaryContainer = Color(0xFF3B0C25),
        background = Color(0xFFFAEFF5),
        onBackground = Color(0xFF3B0C25),
        surface = Color(0xFFFAEFF5),
        onSurface = Color(0xFF3B0C25),
        surfaceVariant = Color(0xFFE9D2DF),
        onSurfaceVariant = Color(0xFF723154),
        outline = Color(0xFF995C7C),
        outlineVariant = Color(0xFFDBBDCD),
        inverseSurface = Color(0xFF4F1735),
        inverseOnSurface = Color(0xFFFAEFF5),
        surfaceBright = Color(0xFFFCF3F8),
        surfaceDim = Color(0xFFF2D4E4),
        surfaceContainerLowest = Color(0xFFFFFFFF),
        surfaceContainerLow = Color(0xFFF9ECF3),
        surfaceContainer = Color(0xFFF6E4EE),
        surfaceContainerHigh = Color(0xFFF1DAE6),
        surfaceContainerHighest = Color(0xFFEDCFDF),
    )
