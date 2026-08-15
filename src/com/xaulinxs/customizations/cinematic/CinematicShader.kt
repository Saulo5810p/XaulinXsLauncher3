/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Motor de shader AGSL portado quase sem alterações do projeto irmão
 * XaulinXs RetroPlayer (com.example.ui.effects.CinematicShader). O shader
 * em si já era puro android.graphics.RuntimeShader/RenderEffect — só o
 * wrapper createComposeCinematicEffect (que dependia de Jetpack Compose)
 * foi omitido aqui, já que o Launcher3 usa View System, não Compose.
 * createCinematicEffect() é usado diretamente via View.setRenderEffect().
 */
package com.xaulinxs.customizations.cinematic

import android.graphics.ColorMatrix
import android.graphics.ColorMatrixColorFilter
import android.graphics.RenderEffect
import android.graphics.RuntimeShader
import android.graphics.Shader
import android.os.Build
import androidx.compose.ui.graphics.asComposeRenderEffect

object CinematicShader {

    const val AGSL_CINEMATIC_MASTER = """
        uniform shader uContents;
        uniform vec2 uResolution;
        uniform float uRotationSpeed;   // Velocidade angular de rotação
        uniform float uScaleFactor;     // Escala de zoom / pulo
        uniform float uBlurIntensity;   // Intensidade do desfoque de movimento
        uniform float uChromaticShift;  // Distorção dos canais RGB (Aberração Cromática)
        uniform float uVignetteIntensity;// Escurecimento periférico cinematográfico

        vec4 main(vec2 fragCoord) {
            // Se o movimento cessou, retorna imediatamente o frame nítido sem overhead
            if (uBlurIntensity < 0.005 && uChromaticShift < 0.005 && uVignetteIntensity < 0.005) {
                return uContents.eval(fragCoord);
            }

            vec2 center = uResolution * 0.5;
            vec2 uv = (fragCoord - center) / max(uResolution.y, 1.0);
            float dist = length(uv);

            // Vetores de direção radial e tangencial para Spin & Zoom
            vec2 dir = normalize(uv + vec2(0.0001));
            vec2 tangent = vec2(-dir.y, dir.x);

            vec4 colorSum = vec4(0.0);
            float weightSum = 0.0;
            const int SAMPLES = 16;

            float chromFactor = uChromaticShift * (0.02 + dist * 0.15);

            for (int i = 0; i < SAMPLES; i++) {
                float t = (float(i) / float(SAMPLES - 1)) - 0.5;

                // Deslocamento de amostragem combinando Giro Tangencial e Zoom Radial
                vec2 sampleOffset = (tangent * uRotationSpeed + dir * (uScaleFactor - 1.0)) * t * uBlurIntensity * 46.0;

                // Aberração Cromática 3D: Separação espectral dos canais R, G e B
                vec2 coordR = fragCoord + sampleOffset * (1.0 + chromFactor);
                vec2 coordG = fragCoord + sampleOffset;
                vec2 coordB = fragCoord + sampleOffset * (1.0 - chromFactor);

                float r = uContents.eval(coordR).r;
                float g = uContents.eval(coordG).g;
                float b = uContents.eval(coordB).b;
                float a = uContents.eval(coordG).a;

                float weight = 1.0 - abs(t) * 0.75;
                colorSum += vec4(r, g, b, a) * weight;
                weightSum += weight;
            }

            vec4 finalColor = colorSum / weightSum;

            // Aplica Vinheta Cinematográfica nas bordas durante altas velocidades
            if (uVignetteIntensity > 0.01) {
                float vignetteFactor = smoothstep(0.8, 0.2, dist * uVignetteIntensity);
                finalColor.rgb *= mix(0.55, 1.0, vignetteFactor);
            }

            return finalColor;
        }
    """

    /**
     * Factory para criar RenderEffect AGSL ou Fallback Nativo (API 31+)
     */
    fun createCinematicEffect(
        width: Float,
        height: Float,
        rotationSpeed: Float,
        scaleFactor: Float,
        blurIntensity: Float,
        chromaticShift: Float,
        vignetteIntensity: Float = 0.0f
    ): RenderEffect? {
        if (blurIntensity < 0.01f && chromaticShift < 0.01f && vignetteIntensity < 0.01f) {
            return null
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            try {
                val runtimeShader = RuntimeShader(AGSL_CINEMATIC_MASTER)
                runtimeShader.setFloatUniform("uResolution", width.coerceAtLeast(1f), height.coerceAtLeast(1f))
                runtimeShader.setFloatUniform("uRotationSpeed", rotationSpeed)
                runtimeShader.setFloatUniform("uScaleFactor", scaleFactor)
                runtimeShader.setFloatUniform("uBlurIntensity", blurIntensity)
                runtimeShader.setFloatUniform("uChromaticShift", chromaticShift)
                runtimeShader.setFloatUniform("uVignetteIntensity", vignetteIntensity)

                return RenderEffect.createRuntimeShaderEffect(runtimeShader, "uContents")
            } catch (_: Exception) {
                // Fallback para API 31 se falhar
            }
        }

        // Fallback para Android 12 (API 31): RenderEffect Blur + ColorFilter
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val totalBlur = (blurIntensity * 26f).coerceIn(0.1f, 60f)
            if (totalBlur <= 0.5f) return null

            val blurEffect = RenderEffect.createBlurEffect(
                totalBlur,
                totalBlur,
                Shader.TileMode.MIRROR
            )

            if (chromaticShift > 0.05f) {
                val chromMatrix = ColorMatrix(
                    floatArrayOf(
                        1f + chromaticShift * 0.35f, 0f, 0f, 0f, 0f,
                        0f, 1f, 0f, 0f, 0f,
                        0f, 0f, 1f + chromaticShift * 0.55f, 0f, 0f,
                        0f, 0f, 0f, 1f, 0f
                    )
                )
                val colorFilterEffect = RenderEffect.createColorFilterEffect(ColorMatrixColorFilter(chromMatrix))
                return RenderEffect.createChainEffect(blurEffect, colorFilterEffect)
            }

            return blurEffect
        }

        return null
    }

    /**
     * Variante Compose do factory acima — devolve ComposeRenderEffect em
     * vez de android.graphics.RenderEffect, para uso direto em
     * Modifier.graphicsLayer { renderEffect = ... } dentro de Composables.
     * Portado do projeto irmão RetroPlayer (CinematicShader.kt original,
     * createComposeCinematicEffect) — omitido na primeira portagem deste
     * arquivo porque o Launcher3 até então só usava View System puro; a
     * feature de painel de widgets (100% Compose) volta a precisar dela.
     */
    fun createComposeCinematicEffect(
        width: Float,
        height: Float,
        rotationSpeed: Float,
        scaleFactor: Float,
        blurIntensity: Float,
        chromaticShift: Float,
        vignetteIntensity: Float = 0.0f
    ): androidx.compose.ui.graphics.RenderEffect? {
        val effect = createCinematicEffect(
            width = width,
            height = height,
            rotationSpeed = rotationSpeed,
            scaleFactor = scaleFactor,
            blurIntensity = blurIntensity,
            chromaticShift = chromaticShift,
            vignetteIntensity = vignetteIntensity
        ) ?: return null
        return effect.asComposeRenderEffect()
    }

// XAULINXS_COMPOSE_EFFECT_ADDED
}
