"""
XaulinXs Customizations — Feature Cinematográfica 2/N: motion blur +
aberração cromática ao rolar entre páginas/abas, portado do princípio já
validado no projeto irmão RetroPlayer Compose (CinematicScrollEffects.kt).

O motor de shader AGSL (CinematicShader.kt) é reaproveitado quase
inalterado — já era código android.graphics puro, sem dependência de
Compose. Só a camada de "quando aplicar" foi reescrita: em vez de reagir
a um LazyListState do Compose, observa a velocidade de scroll nativa do
PagedView (base do Workspace) via OverScroller e o delta de toque durante
o arrasto manual.

Perfil fixo INSANE (mesma decisão do RetroPlayer — sem versão reduzida).

Idempotente: pode rodar de novo sem duplicar nada.

USO (Termux, dentro da pasta raiz do projeto XaulinXsLauncher3):
    python3 feature_cinematic_2_scroll_motion_blur.py
"""
from pathlib import Path

def write_if_absent(path_str, content):
    path = Path(path_str)
    if path.exists():
        print(f"SKIP (já existe): {path_str}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"CRIADO: {path_str}")

def replace_once(path_str, old, new, label):
    path = Path(path_str)
    assert path.exists(), f"arquivo não encontrado: {path_str} (rode este script na raiz do projeto)"
    content = path.read_text(encoding="utf-8")
    if new in content:
        print(f"SKIP ({label}): já aplicado")
        return
    assert old in content, f"âncora não encontrada em {path_str} ({label}) — o arquivo pode ter mudado desde a última sessão, cola o PagedView.java atual"
    assert content.count(old) == 1, f"âncora aparece {content.count(old)}x em {path_str} ({label}), precisa ser única"
    content = content.replace(old, new)
    path.write_text(content, encoding="utf-8")
    print(f"APLICADO: {label}")


# ---------------------------------------------------------------------------
# 1) Motor de shader AGSL — praticamente idêntico ao do RetroPlayer, só sem
#    o wrapper Compose (que não existe/não é necessário em View System)
# ---------------------------------------------------------------------------
write_if_absent(
    "src/com/xaulinxs/customizations/cinematic/CinematicShader.kt",
    '''/*
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

object CinematicShader {

    const val AGSL_CINEMATIC_MASTER = \"\"\"
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
    \"\"\"

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
}
''',
)

# ---------------------------------------------------------------------------
# 2) Camada de aplicação — velocidade de scroll do PagedView -> RenderEffect
# ---------------------------------------------------------------------------
write_if_absent(
    "src/com/xaulinxs/customizations/cinematic/CinematicScrollVelocityEffect.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Motion blur + aberração cromática reagindo à velocidade do arrasto entre
 * páginas/abas, portado do princípio já validado no projeto irmão
 * RetroPlayer Compose (CinematicScrollEffects.kt / cinematicScrollVelocity).
 *
 * Diferença de plataforma: o RetroPlayer aplica isso via Modifier.graphicsLayer
 * reagindo a LazyListState (Compose). Aqui não existe LazyListState — o
 * PagedView (base do Workspace) já expõe a mesma informação de velocidade
 * nativamente via OverScroller.getCurrVelocity() durante o fling, e via o
 * delta de posição a cada ACTION_MOVE durante o arrasto manual do dedo.
 * Esta classe centraliza a suavização (mesmo algoritmo de decaimento
 * exponencial do RetroPlayer) e a aplicação do RenderEffect na própria
 * PagedView/Workspace via setRenderEffect — sem tocar no scroll real.
 *
 * Perfil fixo INSANE (mesma decisão do RetroPlayer: sem versão reduzida).
 */
package com.xaulinxs.customizations.cinematic

import android.os.Build
import android.view.View
import kotlin.math.abs
import kotlin.math.min

object CinematicScrollVelocityEffect {

    // Mesmos multiplicadores do perfil INSANE do RetroPlayer
    // (ScrollCinematicProfile.INSANE em CinematicScrollEffects.kt).
    private const val BLUR_MULTIPLIER = 1.8f
    private const val CHROMATIC_MULTIPLIER = 1.6f
    private const val VIGNETTE_MULTIPLIER = 0.7f
    private const val VELOCITY_THRESHOLD = 450f

    // Mesma suavização exponencial do RetroPlayer: sobe rápido (resposta
    // imediata ao gesto), desce suave (o efeito "esvai" em vez de cortar
    // seco quando o dedo/fling para).
    private const val DECAY_KEEP = 0.82f
    private const val DECAY_NEW = 0.18f

    // WeakHashMap: evita reter a View (e sua Activity/Context) na memória
    // caso o Launcher recrie a PagedView (rotação, mudança de config) sem
    // que este objeto singleton seja notificado — a entrada é coletada
    // junto com a View quando não há mais nenhuma outra referência forte.
    private val states = java.util.WeakHashMap<View, State>()

    private class State {
        var lastOffset = 0f
        var smoothedVelocity = 0f
    }

    /**
     * Chamar a cada frame de scroll (arrasto manual OU fling do
     * OverScroller) com a posição de scroll absoluta atual em pixels.
     * Aplica o RenderEffect diretamente na `target` (tipicamente a própria
     * PagedView/Workspace) proporcional à velocidade suavizada.
     */
    @JvmStatic
    fun onScrollPositionChanged(target: View, absoluteScrollPx: Float) {
        val state = states.getOrPut(target) { State() }

        val delta = abs(absoluteScrollPx - state.lastOffset)
        state.lastOffset = absoluteScrollPx

        state.smoothedVelocity = if (delta > state.smoothedVelocity) {
            delta
        } else {
            state.smoothedVelocity * DECAY_KEEP + delta * DECAY_NEW
        }

        val velocity = min(state.smoothedVelocity / VELOCITY_THRESHOLD, 1f)
        applyEffect(target, velocity)
    }

    /**
     * Chamar quando o scroll termina de vez (fling concluído, dedo solto
     * sem fling) para garantir que o efeito zera mesmo sem mais eventos de
     * posição chegando.
     */
    @JvmStatic
    fun onScrollSettled(target: View) {
        states[target]?.smoothedVelocity = 0f
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            target.setRenderEffect(null)
        }
    }

    private fun applyEffect(target: View, velocity: Float) {
        // setRenderEffect(RenderEffect) só existe a partir da API 31 —
        // em aparelhos mais antigos (minSdk 28) este efeito específico
        // simplesmente não roda, sem crash e sem afetar o scroll real.
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return

        if (velocity < 0.02f) {
            target.setRenderEffect(null)
            return
        }
        val w = target.width.toFloat().coerceAtLeast(100f)
        val h = target.height.toFloat().coerceAtLeast(100f)

        val effect = CinematicShader.createCinematicEffect(
            width = w,
            height = h,
            rotationSpeed = 0f,
            scaleFactor = 1f,
            blurIntensity = velocity * BLUR_MULTIPLIER,
            chromaticShift = velocity * CHROMATIC_MULTIPLIER,
            vignetteIntensity = velocity * VIGNETTE_MULTIPLIER
        )
        target.setRenderEffect(effect)
    }
}
''',
)

# ---------------------------------------------------------------------------
# 3) Hooks no PagedView.java (base do Workspace) — três pontos, todos
#    puramente observacionais, nenhum altera a lógica de scroll real
# ---------------------------------------------------------------------------

# 3a) Fling automático (OverScroller) dentro de computeScrollHelper()
replace_once(
    "src/com/android/launcher3/PagedView.java",
    """            invalidate();
            return true;
        } else if (mNextPage != INVALID_PAGE) {""",
    """            invalidate();
            // XaulinXs Customizations: motion blur + aberração cromática
            // proporcional à velocidade do fling entre páginas, portado do
            // RetroPlayer. Puramente observacional — não altera newPos nem
            // qualquer lógica de scroll real acima.
            com.xaulinxs.customizations.cinematic.CinematicScrollVelocityEffect
                    .onScrollPositionChanged(this, (float) newPos);
            return true;
        } else if (mNextPage != INVALID_PAGE) {""",
    "hook de fling em computeScrollHelper (PagedView.java)",
)

# 3b) Fim do computeScrollHelper() — zera o efeito quando não há mais
#     nenhum scroll/fling em andamento
replace_once(
    "src/com/android/launcher3/PagedView.java",
    """            if (canAnnouncePageDescription()) {
                announcePageForAccessibility();
            }
        }
        return false;
    }""",
    """            if (canAnnouncePageDescription()) {
                announcePageForAccessibility();
            }
        }
        // XaulinXs Customizations: scroll/fling parou de vez (nenhum dos
        // dois ramos acima segue em andamento) — zera o efeito cinematográfico.
        com.xaulinxs.customizations.cinematic.CinematicScrollVelocityEffect
                .onScrollSettled(this);
        return false;
    }""",
    "hook de scroll parado no fim de computeScrollHelper (PagedView.java)",
)

# 3c) Arrasto manual (dedo na tela) dentro do ACTION_MOVE
replace_once(
    "src/com/android/launcher3/PagedView.java",
    """                if (delta != 0) {
                    mOrientationHandler.setPrimary(this, VIEW_SCROLL_BY, delta);

                    if (mAllowOverScroll) {""",
    """                if (delta != 0) {
                    mOrientationHandler.setPrimary(this, VIEW_SCROLL_BY, delta);
                    // XaulinXs Customizations: motion blur + aberração
                    // cromática também durante o arrasto manual (dedo ainda
                    // na tela, antes de qualquer fling do OverScroller).
                    // Puramente observacional, roda depois do scroll real.
                    com.xaulinxs.customizations.cinematic.CinematicScrollVelocityEffect
                            .onScrollPositionChanged(this,
                                    (float) mOrientationHandler.getPrimaryScroll(this));

                    if (mAllowOverScroll) {""",
    "hook de arrasto manual no ACTION_MOVE (PagedView.java)",
)

print("\nOK — Feature 2/N (motion blur + aberração cromática no scroll de páginas) aplicada.")
print("Cobre tanto o arrasto manual (dedo na tela) quanto o fling automático,")
print("no Workspace e em qualquer outra tela que herde de PagedView.")
print("Próximo passo: ./gradlew assembleNoQuickstepDebug")
