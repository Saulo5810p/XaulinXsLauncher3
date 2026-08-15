#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XaulinXs Customizations — Feature 4/N (item 2 da prioridade):
abrir/fechar painel de widgets (WidgetsFullSheet moderno, 100% Compose).

Diferente do AllApps (View System puro), o painel de widgets deste AOSP 17
roda como Activity Compose separada (QuickstepWidgetPickerActivity /
QuickstepAddItemActivity), montada em modules/widgetpicker/. Efeito
implementado:

  1) Painel inteiro: motion blur + aberração cromática cinematográfica no
     scrim de fundo durante a transição de abrir/fechar (reagindo ao
     onSheetProgress já existente no TitledBottomSheet).
  2) Cada card de widget na grade (WidgetsGrid -> Previews): giro 720° em
     cascata (mesma matemática do AllAppsIconEnterEffect: overshoot 1.5x,
     blur 3.6x, aberração cromática 3.0x, spring dampingRatio 0.55),
     disparado toda vez que a direção do gesto de abrir/fechar inverte —
     mesmo padrão de detecção por mudança de direção do AllAppsCascadeTrigger,
     agora em Compose puro (Animatable + spring(), sem SpringAnimation do
     dynamicanimation, que é específico de View System).

Todas as edições são ADITIVAS: nenhum arquivo AOSP original tem lógica
reescrita, só hooks pontuais de 1 linha. Script idempotente — pode rodar
várias vezes sem duplicar nada.

Uso:
    python3 feature_cinematic_4_widgets_sheet_open_close.py /caminho/do/repo
    (ou rode de dentro da raiz do repo sem argumento)
"""

import os
import sys
import re

MARKER_SHEET_HOOK = "// XAULINXS_CASCADE_HOOK_WIDGETS_SHEET"
MARKER_GRID_HOOK = "// XAULINXS_CASCADE_HOOK_WIDGETS_GRID"
MARKER_SHADER_COMPOSE = "// XAULINXS_COMPOSE_EFFECT_ADDED"

NEW_FILE_PATH = "src/com/xaulinxs/customizations/cinematic/CinematicWidgetSheetEffects.kt"

NEW_FILE_CONTENT = '''/*
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
private const val STAGGER_DELAY_MS = 18L
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
                            dampingRatio = 0.55f,
                            stiffness = Spring.StiffnessLow,
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
''' + f"\n{MARKER_SHADER_COMPOSE}\n"

# --------------------------------------------------------------------------

COMPOSE_SHADER_ADDITION = '''
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
'''

TITLED_BOTTOM_SHEET_REL_PATH = (
    "modules/widgetpicker/src/com/android/launcher3/widgetpicker/ui/components/"
    "bottomsheet/TitledBottomSheet.kt"
)

WIDGETS_GRID_REL_PATH = (
    "modules/widgetpicker/src/com/android/launcher3/widgetpicker/ui/components/WidgetsGrid.kt"
)


def find_repo_root(start):
    candidates = [start] + [os.path.join(start, d) for d in os.listdir(start)] if os.path.isdir(start) else [start]
    for c in candidates:
        if os.path.isfile(os.path.join(c, TITLED_BOTTOM_SHEET_REL_PATH)):
            return c
    return None


def write_new_file(repo_root):
    path = os.path.join(repo_root, NEW_FILE_PATH)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read()
        if MARKER_SHADER_COMPOSE in existing:
            print(f"[=] {NEW_FILE_PATH} já existe e está atualizado — pulando.")
            return
        print(f"[~] {NEW_FILE_PATH} existe mas parece desatualizado — sobrescrevendo.")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(NEW_FILE_CONTENT)
    print(f"[+] Criado {NEW_FILE_PATH}")


def patch_shader_compose_variant(repo_root):
    path = os.path.join(repo_root, "src/com/xaulinxs/customizations/cinematic/CinematicShader.kt")
    if not os.path.isfile(path):
        print(f"[!] AVISO: {path} não encontrado — pulando patch do shader Compose.")
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if MARKER_SHADER_COMPOSE in content:
        print("[=] CinematicShader.kt já tem createComposeCinematicEffect — pulando.")
        return

    # Import necessário para asComposeRenderEffect()
    import_line = "import androidx.compose.ui.graphics.asComposeRenderEffect\n"
    if import_line.strip() not in content:
        content = content.replace(
            "import android.os.Build\n",
            "import android.os.Build\n" + import_line,
            1,
        )

    # Insere a variante Compose logo antes do fechamento do object (último "}" do arquivo).
    marker_comment = f"\n{MARKER_SHADER_COMPOSE}\n"
    insertion = COMPOSE_SHADER_ADDITION + marker_comment
    last_brace_idx = content.rstrip().rfind("}")
    if last_brace_idx == -1:
        print("[!] AVISO: não achei o fechamento do object CinematicShader — patch abortado.")
        return
    new_content = content[:last_brace_idx] + insertion + content[last_brace_idx:]

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("[+] CinematicShader.kt: adicionado createComposeCinematicEffect()")


def patch_titled_bottom_sheet(repo_root):
    path = os.path.join(repo_root, TITLED_BOTTOM_SHEET_REL_PATH)
    if not os.path.isfile(path):
        print(f"[!] ERRO: {path} não encontrado. Estrutura do repo mudou? Abortando este hook.")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if MARKER_SHEET_HOOK in content:
        print("[=] TitledBottomSheet.kt já tem o hook da cascata — pulando.")
        return True

    # 1) Imports necessários
    import_anchor = "import com.android.launcher3.widgetpicker.ui.components.SheetDismissState\n"
    new_imports = (
        "import com.xaulinxs.customizations.cinematic.CinematicWidgetSheetScrim\n"
        "import com.xaulinxs.customizations.cinematic.LocalCinematicWidgetsCascadeTrigger\n"
        "import com.xaulinxs.customizations.cinematic.rememberWidgetsSheetCascadeTrigger\n"
    )
    if import_anchor not in content:
        print("[!] ERRO: âncora de import não encontrada em TitledBottomSheet.kt — abortando este hook.")
        return False
    content = content.replace(import_anchor, import_anchor + new_imports, 1)

    # 2) Troca o Box de scrim simples por CinematicWidgetSheetScrim, e insere o
    #    CompositionLocalProvider com o trigger de cascata em volta de todo o resto.
    old_scrim_block = (
        "        Box( // scrim\n"
        "            modifier =\n"
        "                Modifier.fillMaxSize()\n"
        "                    .alpha(scrimAlpha)\n"
        "                    .background(WidgetPickerTheme.colors.sheetBackgroundScrim)\n"
        "        )\n"
    )
    new_scrim_block = (
        f"        {MARKER_SHEET_HOOK}\n"
        "        val cinematicCascadeTrigger = rememberWidgetsSheetCascadeTrigger(scrimAlpha)\n"
        "        CinematicWidgetSheetScrim(\n"
        "            scrimAlpha = scrimAlpha,\n"
        "            scrimColor = WidgetPickerTheme.colors.sheetBackgroundScrim,\n"
        "        )\n"
    )
    if old_scrim_block not in content:
        print("[!] ERRO: bloco do scrim original não encontrado (formatação mudou?) — abortando este hook.")
        return False
    content = content.replace(old_scrim_block, new_scrim_block, 1)

    # 3) Envolve o restante do corpo da função (a partir de BoxWithConstraints até o
    #    fechamento do Box externo) com CompositionLocalProvider, para que todos os
    #    cards descendentes (WidgetsGrid/Previews) recebam o trigger de cascata.
    old_boxwc_start = "        BoxWithConstraints(\n"
    new_boxwc_start = (
        "        CompositionLocalProvider(\n"
        "            LocalCinematicWidgetsCascadeTrigger provides cinematicCascadeTrigger\n"
        "        ) {\n"
        "        BoxWithConstraints(\n"
    )
    if old_boxwc_start not in content:
        print("[!] ERRO: início do BoxWithConstraints não encontrado — abortando este hook.")
        return False
    content = content.replace(old_boxwc_start, new_boxwc_start, 1)

    # Fecha o CompositionLocalProvider logo após o "}" que fecha o Box externo
    # (contentAlignment = Alignment.BottomCenter), antes do "}" que fecha a função.
    old_fn_end = (
        "        }\n"
        "    }\n"
        "}\n\n"
        "@Composable\n"
        "private fun SwipeUpToDismissHandler("
    )
    new_fn_end = (
        "        }\n"
        "        }\n"
        "    }\n"
        "}\n\n"
        "@Composable\n"
        "private fun SwipeUpToDismissHandler("
    )
    if old_fn_end not in content:
        print("[!] ERRO: fechamento da função TitledBottomSheet não encontrado — abortando este hook.")
        return False
    content = content.replace(old_fn_end, new_fn_end, 1)

    # 4) Import do CompositionLocalProvider (já existe androidx.compose.runtime.Composable,
    #    mas CompositionLocalProvider pode não estar importado ainda).
    if "import androidx.compose.runtime.CompositionLocalProvider\n" not in content:
        content = content.replace(
            "import androidx.compose.runtime.Composable\n",
            "import androidx.compose.runtime.Composable\n"
            "import androidx.compose.runtime.CompositionLocalProvider\n",
            1,
        )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] TitledBottomSheet.kt: scrim cinematográfico + CompositionLocalProvider da cascata adicionados")
    return True


def patch_widgets_grid(repo_root):
    path = os.path.join(repo_root, WIDGETS_GRID_REL_PATH)
    if not os.path.isfile(path):
        print(f"[!] ERRO: {path} não encontrado. Abortando este hook.")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if MARKER_GRID_HOOK in content:
        print("[=] WidgetsGrid.kt já tem o hook da cascata por item — pulando.")
        return True

    # Import
    import_anchor = "import com.android.launcher3.widgetpicker.ui.WidgetInteractionSource\n"
    new_import = "import com.xaulinxs.customizations.cinematic.cascadeSpinEnter\n"
    if import_anchor not in content:
        print("[!] ERRO: âncora de import não encontrada em WidgetsGrid.kt — abortando este hook.")
        return False
    if new_import not in content:
        content = content.replace(import_anchor, import_anchor + new_import, 1)

    # Precisamos do índice do item dentro de Previews() para o delay em cascata.
    # Trocamos `widgets.forEach { widgetItem ->` por `widgets.forEachIndexed { index, widgetItem ->`
    old_previews_loop = "    widgets.forEach { widgetItem ->\n        val id = widgetItem.id\n"
    new_previews_loop = (
        f"    {MARKER_GRID_HOOK}\n"
        "    widgets.forEachIndexed { index, widgetItem ->\n"
        "        val id = widgetItem.id\n"
    )
    if old_previews_loop not in content:
        print("[!] ERRO: loop de Previews() não encontrado (assinatura mudou?) — abortando este hook.")
        return False
    content = content.replace(old_previews_loop, new_previews_loop, 1)

    # Aplica o modifier de cascata no Box que envolve cada WidgetPreview.
    old_box = (
        "        Box(\n"
        "            contentAlignment = Alignment.BottomCenter,\n"
        "            modifier =\n"
        "                Modifier.fillMaxSize().clearAndSetSemantics {\n"
        "                    testTag = buildWidgetPickerTestTag(WIDGET_PREVIEW_TEST_TAG)\n"
        "                },\n"
        "        ) {\n"
    )
    new_box = (
        "        Box(\n"
        "            contentAlignment = Alignment.BottomCenter,\n"
        "            modifier =\n"
        "                Modifier.fillMaxSize()\n"
        "                    .cascadeSpinEnter(indexInGrid = index)\n"
        "                    .clearAndSetSemantics {\n"
        "                        testTag = buildWidgetPickerTestTag(WIDGET_PREVIEW_TEST_TAG)\n"
        "                    },\n"
        "        ) {\n"
    )
    if old_box not in content:
        print("[!] ERRO: bloco Box do WidgetPreview não encontrado — abortando este hook.")
        return False
    content = content.replace(old_box, new_box, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] WidgetsGrid.kt: cascadeSpinEnter aplicado a cada card da grade")
    return True


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    repo_root = find_repo_root(start)
    if repo_root is None:
        print(
            "[!] ERRO: não encontrei a estrutura esperada do XaulinXsLauncher3 "
            f"(procurado a partir de: {start}).\n"
            "    Rode este script de dentro da raiz do repo clonado, ou passe o "
            "caminho como argumento:\n"
            "    python3 feature_cinematic_4_widgets_sheet_open_close.py /caminho/do/repo"
        )
        sys.exit(1)

    print(f"[i] Repo detectado em: {repo_root}\n")

    write_new_file(repo_root)
    patch_shader_compose_variant(repo_root)
    ok1 = patch_titled_bottom_sheet(repo_root)
    ok2 = patch_widgets_grid(repo_root)

    print("")
    if ok1 and ok2:
        print("[OK] Feature 4/N aplicada com sucesso. Rode:")
        print("     ./gradlew :quickstep:assembleDebug")
        print("     (ou o módulo correspondente que você usa para compilar o Launcher3)")
    else:
        print("[FALHOU] Um ou mais hooks não foram aplicados — veja os erros [!] acima.")
        print("         Nenhuma alteração parcial quebrada foi deixada nos arquivos que falharam,")
        print("         mas confira com 'git diff' antes de compilar.")
        sys.exit(2)


if __name__ == "__main__":
    main()
