/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Efeito de abrir/fechar do painel de widgets (WidgetsFullSheet moderno,
 * 100% Jetpack Compose — diferente do AllApps, que é View System puro).
 * Duas partes:
 *
 *  1) CinematicWidgetSheetScrim: motion blur + aberração cromática no
 *     scrim de fundo do TitledBottomSheet, reagindo ao progresso real da
 *     transição (0 = fechado, 1 = aberto — mesma convenção do
 *     onSheetProgress já existente no componente).
 *
 *  2) cascadeSpinEnter(): modifier aplicado a cada card individual da
 *     grade de widgets (WidgetsGrid -> Previews), reproduzindo a mesma
 *     matemática do AllAppsIconEnterEffect (View System): giro 720°,
 *     overshoot 1.5x, blur 3.6x, aberração cromática 3.0x — só que aqui
 *     com Animatable + spring() nativos do Compose, em vez de
 *     SpringAnimation do androidx.dynamicanimation (que não faz sentido
 *     fora de View System).
 *
 * Disparo em cascata: LocalCinematicWidgetsCascadeTrigger é um estado
 * (Int, incrementado a cada mudança de direção do gesto abrir/fechar)
 * provido pelo TitledBottomSheet e observado por cada card via
 * CompositionLocal — mesmo espírito da detecção por mudança de direção do
 * AllAppsCascadeTrigger.kt, adaptado ao modelo declarativo do Compose
 * (aqui não existe "child view visível agora" pra iterar; em vez disso,
 * cada item observa o mesmo contador e recalcula seu próprio delay via
 * índice de posição, que o item já conhece).
 */
package com.xaulinxs.customizations.cinematic

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.unit.IntSize
import kotlinx.coroutines.delay
import kotlin.math.PI
import kotlin.math.max
import kotlin.math.sin

/**
 * Contador incrementado a cada mudança de direção do gesto de abrir/fechar
 * o painel de widgets. Cada card observa este valor: quando muda, dispara
 * sua própria animação de entrada com delay proporcional ao índice dele.
 * `-1` = estado inicial, nenhuma cascata disparada ainda.
 */
val LocalCinematicWidgetsCascadeTrigger = compositionLocalOf { mutableIntStateOf(-1) }

/**
 * Detecção de mudança de direção do progresso do sheet — mesma lógica do
 * AllAppsCascadeTrigger.onProgressChanged, adaptada para incrementar um
 * estado Compose observável em vez de percorrer child views diretamente.
 */
@Composable
fun rememberWidgetsSheetCascadeTrigger(progress: Float): androidx.compose.runtime.MutableIntState {
    val cascadeCounter = remember { mutableIntStateOf(-1) }
    var previousProgress by remember { mutableFloatStateOf(progress) }
    var lastDirection by remember { mutableIntStateOf(0) }

    LaunchedEffect(progress) {
        if (progress != previousProgress) {
            val direction = if (progress > previousProgress) 1 else -1
            if (direction != lastDirection) {
                lastDirection = direction
                cascadeCounter.intValue += 1
            }
            previousProgress = progress
        }
    }

    return cascadeCounter
}

/**
 * Scrim de fundo do painel de widgets com motion blur + aberração
 * cromática cinematográfica reagindo à velocidade/progresso da transição
 * de abrir/fechar. Substitui o Box de scrim simples (alpha only) que
 * existia antes — mantém o mesmo comportamento de alpha, só adiciona o
 * efeito de shader por cima durante o movimento.
 */
@Composable
fun CinematicWidgetSheetScrim(
    scrimAlpha: Float,
    scrimColor: androidx.compose.ui.graphics.Color,
    modifier: Modifier = Modifier,
) {
    var previousAlpha by remember { mutableFloatStateOf(scrimAlpha) }
    var velocity by remember { mutableFloatStateOf(0f) }
    var size by remember { mutableStateOf(IntSize.Zero) }

    LaunchedEffect(scrimAlpha) {
        velocity = scrimAlpha - previousAlpha
        previousAlpha = scrimAlpha
        // A velocidade decai sozinha se o progresso parar de mudar (sheet
        // assentado), evitando blur "grudado" quando o gesto para no meio.
        delay(60)
        if (previousAlpha == scrimAlpha) velocity = 0f
    }

    Box(
        modifier =
            modifier
                .fillMaxSize()
                .onSizeChanged { size = it }
                .alpha(scrimAlpha)
                .graphicsLayer {
                    val blurIntensity = kotlin.math.abs(velocity) * 8f
                    if (blurIntensity > 0.02f) {
                        val w = size.width.toFloat().coerceAtLeast(100f)
                        val h = size.height.toFloat().coerceAtLeast(100f)
                        renderEffect =
                            CinematicShader.createComposeCinematicEffect(
                                width = w,
                                height = h,
                                rotationSpeed = 0f,
                                scaleFactor = 1f,
                                blurIntensity = blurIntensity,
                                chromaticShift = blurIntensity * 0.6f,
                                vignetteIntensity = blurIntensity * 0.3f,
                            )
                    } else {
                        renderEffect = null
                    }
                }
                .background(scrimColor)
    )
}

// Mesmos valores calibrados do AllAppsIconEnterEffect (View System) —
// reproduzidos aqui em unidades nativas do Compose.
private const val MAX_ROTATION_DEGREES = 720f
private const val OVERSHOOT_SCALE = 1.5f
private const val BLUR_MULTIPLIER = 3.6f
private const val CHROMATIC_MULTIPLIER = 3.0f
private const val VIGNETTE_MULTIPLIER = 1.0f
private const val STAGGER_DELAY_MS = 110L // suavizado (era 18L) — cascata varre bem mais devagar
private const val MAX_STAGGER_ITEMS = 30

/**
 * Modifier a aplicar em cada card individual da grade de widgets. Observa
 * o LocalCinematicWidgetsCascadeTrigger; toda vez que o contador muda,
 * dispara a animação de giro 720° com delay proporcional a `indexInGrid`.
 */
fun Modifier.cascadeSpinEnter(indexInGrid: Int): Modifier =
    this.composed {
            val cascadeCounter = LocalCinematicWidgetsCascadeTrigger.current
            val triggerValue = cascadeCounter.intValue

            val progress = remember { Animatable(1f) }
            var size by remember { mutableStateOf(IntSize.Zero) }

            LaunchedEffect(triggerValue) {
                if (triggerValue < 0) return@LaunchedEffect
                val staggerIndex = indexInGrid.coerceIn(0, MAX_STAGGER_ITEMS)
                delay(staggerIndex * STAGGER_DELAY_MS)
                progress.snapTo(0f)
                progress.animateTo(
                    targetValue = 1f,
                    animationSpec =
                        spring(
                            dampingRatio = 0.78f, // overshoot bem mais contido/suave (era 0.55f)
                            stiffness = 15f, // mais mole que Spring.StiffnessLow (era 200f)
                        ),
                )
            }

            Modifier
                .onSizeChanged { size = it }
                .graphicsLayer {
                    val p = progress.value.coerceIn(0f, 1.4f)
                    val remaining = max(0f, 1f - p)

                    if (remaining <= 0.005f) {
                        rotationZ = 0f
                        rotationY = 0f
                        scaleX = 1f
                        scaleY = 1f
                        alpha = 1f
                        renderEffect = null
                        return@graphicsLayer
                    }

                    rotationZ = remaining * MAX_ROTATION_DEGREES
                    rotationY = remaining * 30f

                    val enterScale =
                        (1f + (OVERSHOOT_SCALE - 1f) *
                            sin(p * PI.toFloat()) * remaining + (1f - remaining))
                            .coerceAtLeast(0.05f)
                    scaleX = enterScale
                    scaleY = enterScale
                    alpha = p.coerceIn(0f, 1f)

                    val w = size.width.toFloat().coerceAtLeast(50f)
                    val h = size.height.toFloat().coerceAtLeast(50f)
                    renderEffect =
                        CinematicShader.createComposeCinematicEffect(
                            width = w,
                            height = h,
                            rotationSpeed = remaining * 4.0f,
                            scaleFactor = enterScale,
                            blurIntensity = remaining * BLUR_MULTIPLIER,
                            chromaticShift = remaining * CHROMATIC_MULTIPLIER,
                            vignetteIntensity = remaining * VIGNETTE_MULTIPLIER,
                        )
                }
        }

// XAULINXS_COMPOSE_EFFECT_ADDED
