/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * "UI-UX Custom Colors" — motor de geração da paleta tonal completa a
 * partir de 2 cores-semente (Primária e Secundária, escolhidas pelo
 * usuário via slider em CustomColorsActivity).
 *
 * Usa o mesmo espaço de cor HCT (Hue/Chroma/Tone) do Material You real,
 * já disponível no projeto via androidx.core.graphics.ColorUtils
 * (colorToM3HCT / M3HCTToColor — mesma API já usada em
 * AutomatedIconDelegate.kt e PredictedAppIcon.java), sem precisar de
 * dependência nova.
 *
 * Terciária e a família Neutra/Neutra-Variante (usadas nas superfícies
 * Surface e Outline) são derivadas automaticamente a partir do matiz da
 * Primária, do mesmo jeito que o algoritmo Material You real deriva do
 * wallpaper: terciária = matiz rotacionado, neutra = mesma matiz com
 * croma bem baixo. O usuário só controla os 2 sliders (Primária,
 * Secundária); o resto sai harmônico automaticamente.
 *
 * As chaves geradas aqui são exatamente as 29 declaradas em
 * res/values/material_dynamic_colors_fallback.xml — essa é, no build
 * NoQuickstep deste projeto, a ÚNICA fonte real de materialColorX (o
 * módulo dynamiccolors/ com o link para o wallpaper do Android 12+
 * nunca entrou no settings.gradle, então nunca compila). Isso é o que
 * torna a interceptação em XaulinXsThemeColorResources.kt suficiente
 * para cobrir 100% dos usos, sem precisar tocar nos ~46 arquivos
 * (drawable XML, layout XML, código) que consomem @color/materialColorX.
 */
package com.xaulinxs.customizations.theme

import androidx.core.graphics.ColorUtils

object XaulinXsColorPalette {

    /** Todas as 29 chaves, iguais às declaradas no fallback XML original. */
    data class Palette(
        val materialColorPrimary: Int,
        val materialColorOnPrimary: Int,
        val materialColorPrimaryFixed: Int,
        val materialColorPrimaryFixedDim: Int,
        val materialColorOnPrimaryFixed: Int,
        val materialColorSecondaryFixed: Int,
        val materialColorOnSecondaryFixedVariant: Int,
        val materialColorSurface: Int,
        val materialColorSurfaceDim: Int,
        val materialColorSurfaceBright: Int,
        val materialColorSurfaceContainerLowest: Int,
        val materialColorSurfaceContainerLow: Int,
        val materialColorSurfaceContainer: Int,
        val materialColorSurfaceContainerHigh: Int,
        val materialColorSurfaceContainerHighest: Int,
        val materialColorOnSurface: Int,
        val materialColorOnSurfaceVariant: Int,
        val materialColorOutline: Int,
        val materialColorOutlineVariant: Int,
        val customColorSurfaceEffect0: Int,
        val customColorSurfaceEffect0Fallback: Int,
        val materialColorTertiaryContainer: Int,
        val materialColorInverseSurface: Int,
        val materialColorSecondary: Int,
        val materialColorTertiary: Int,
        val materialColorOnTertiaryFixed: Int,
        val materialColorTertiaryFixedDim: Int,
        val materialColorSurfaceVariant: Int,
        val materialColorOnTertiary: Int,
        val materialColorOnTertiaryContainer: Int,
    ) {
        /** Mapa nome-de-recurso -> cor ARGB, para o Resources wrapper e o writer de XML. */
        fun toMap(): Map<String, Int> = mapOf(
            "materialColorPrimary" to materialColorPrimary,
            "materialColorOnPrimary" to materialColorOnPrimary,
            "materialColorPrimaryFixed" to materialColorPrimaryFixed,
            "materialColorPrimaryFixedDim" to materialColorPrimaryFixedDim,
            "materialColorOnPrimaryFixed" to materialColorOnPrimaryFixed,
            "materialColorSecondaryFixed" to materialColorSecondaryFixed,
            "materialColorOnSecondaryFixedVariant" to materialColorOnSecondaryFixedVariant,
            "materialColorSurface" to materialColorSurface,
            "materialColorSurfaceDim" to materialColorSurfaceDim,
            "materialColorSurfaceBright" to materialColorSurfaceBright,
            "materialColorSurfaceContainerLowest" to materialColorSurfaceContainerLowest,
            "materialColorSurfaceContainerLow" to materialColorSurfaceContainerLow,
            "materialColorSurfaceContainer" to materialColorSurfaceContainer,
            "materialColorSurfaceContainerHigh" to materialColorSurfaceContainerHigh,
            "materialColorSurfaceContainerHighest" to materialColorSurfaceContainerHighest,
            "materialColorOnSurface" to materialColorOnSurface,
            "materialColorOnSurfaceVariant" to materialColorOnSurfaceVariant,
            "materialColorOutline" to materialColorOutline,
            "materialColorOutlineVariant" to materialColorOutlineVariant,
            "customColorSurfaceEffect0" to customColorSurfaceEffect0,
            "customColorSurfaceEffect0Fallback" to customColorSurfaceEffect0Fallback,
            "materialColorTertiaryContainer" to materialColorTertiaryContainer,
            "materialColorInverseSurface" to materialColorInverseSurface,
            "materialColorSecondary" to materialColorSecondary,
            "materialColorTertiary" to materialColorTertiary,
            "materialColorOnTertiaryFixed" to materialColorOnTertiaryFixed,
            "materialColorTertiaryFixedDim" to materialColorTertiaryFixedDim,
            "materialColorSurfaceVariant" to materialColorSurfaceVariant,
            "materialColorOnTertiary" to materialColorOnTertiary,
            "materialColorOnTertiaryContainer" to materialColorOnTertiaryContainer,
        )
    }

    /**
     * Gera a paleta completa a partir das 2 seeds escolhidas pelo usuário.
     * [primarySeed] e [secondarySeed] são ARGB opacos (ex.: 0xFF6750A4.toInt()).
     */
    @JvmStatic
    fun generate(primarySeed: Int, secondarySeed: Int): Palette {
        val primaryHue = hueOf(primarySeed)
        val primaryChroma = chromaOf(primarySeed).coerceAtLeast(24f)
        val secondaryHue = hueOf(secondarySeed)
        val secondaryChroma = chromaOf(secondarySeed).coerceIn(8f, 24f)

        // Terciária: matiz rotacionado a partir da primária (mesmo padrão do
        // algoritmo M3 real ao derivar do wallpaper), croma moderado.
        val tertiaryHue = (primaryHue + 60f).mod(360f)
        val tertiaryChroma = 24f

        // Neutra / Neutra-Variante: mesmo matiz da primária, croma bem baixo,
        // para dar às superfícies (Surface*, Outline*) um tom sutil ligado
        // à cor escolhida, sem competir visualmente com ela.
        val neutralHue = primaryHue
        val neutralChroma = 4f
        val neutralVariantChroma = 8f

        fun tone(hue: Float, chroma: Float, tone: Float): Int =
            hctToColor(hue, chroma, tone)

        return Palette(
            materialColorPrimary = tone(primaryHue, primaryChroma, 40f),
            materialColorOnPrimary = tone(primaryHue, primaryChroma, 100f),
            materialColorPrimaryFixed = tone(primaryHue, primaryChroma, 90f),
            materialColorPrimaryFixedDim = tone(primaryHue, primaryChroma, 80f),
            materialColorOnPrimaryFixed = tone(primaryHue, primaryChroma, 10f),

            materialColorSecondaryFixed = tone(secondaryHue, secondaryChroma, 90f),
            materialColorOnSecondaryFixedVariant = tone(secondaryHue, secondaryChroma, 30f),
            materialColorSecondary = tone(secondaryHue, secondaryChroma, 40f),

            materialColorSurface = tone(neutralHue, neutralChroma, 98f),
            materialColorSurfaceDim = tone(neutralHue, neutralChroma, 87f),
            materialColorSurfaceBright = tone(neutralHue, neutralChroma, 98f),
            materialColorSurfaceContainerLowest = tone(neutralHue, neutralChroma, 100f),
            materialColorSurfaceContainerLow = tone(neutralHue, neutralChroma, 96f),
            materialColorSurfaceContainer = tone(neutralHue, neutralChroma, 94f),
            materialColorSurfaceContainerHigh = tone(neutralHue, neutralChroma, 92f),
            materialColorSurfaceContainerHighest = tone(neutralHue, neutralChroma, 90f),

            materialColorOnSurface = tone(neutralHue, neutralChroma, 10f),
            materialColorOnSurfaceVariant = tone(neutralHue, neutralVariantChroma, 30f),
            materialColorOutline = tone(neutralHue, neutralVariantChroma, 50f),
            materialColorOutlineVariant = tone(neutralHue, neutralVariantChroma, 80f),

            customColorSurfaceEffect0 = tone(neutralHue, neutralChroma, 94f),
            customColorSurfaceEffect0Fallback = tone(neutralHue, neutralChroma, 94f),

            materialColorTertiaryContainer = tone(tertiaryHue, tertiaryChroma, 90f),
            materialColorInverseSurface = tone(neutralHue, neutralChroma, 20f),
            materialColorTertiary = tone(tertiaryHue, tertiaryChroma, 40f),
            materialColorOnTertiaryFixed = tone(tertiaryHue, tertiaryChroma, 10f),
            materialColorTertiaryFixedDim = tone(tertiaryHue, tertiaryChroma, 80f),
            materialColorSurfaceVariant = tone(neutralHue, neutralVariantChroma, 90f),
            materialColorOnTertiary = tone(tertiaryHue, tertiaryChroma, 100f),
            materialColorOnTertiaryContainer = tone(tertiaryHue, tertiaryChroma, 10f),
        )
    }

    private fun hueOf(color: Int): Float {
        val hct = FloatArray(3)
        ColorUtils.colorToM3HCT(color, hct)
        return hct[0]
    }

    private fun chromaOf(color: Int): Float {
        val hct = FloatArray(3)
        ColorUtils.colorToM3HCT(color, hct)
        return hct[1]
    }

    private fun hctToColor(hue: Float, chroma: Float, tone: Float): Int =
        ColorUtils.M3HCTToColor(hue, chroma, tone)
}
