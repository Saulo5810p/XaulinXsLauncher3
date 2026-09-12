#!/usr/bin/env python3
"""
XaulinXsLauncher3 — Formato de ícone: opção "PAD" + interruptor + fix de
visibilidade da barra. (Flag do popup Compose: ver nota abaixo.)

O QUE ESTE SCRIPT FAZ (rode dentro da raiz do repo clonado, no Termux):

1) Fix de visibilidade: os quadradinhos de formato na tela de
   configurações eram desenhados sem nenhum contorno quando não
   selecionados (só um preenchimento cinza-claro), quase somem contra o
   fundo. Agora todo swatch sempre tem um contorno sutil, e o selecionado
   ganha contorno de destaque + fundo diferenciado.

2) "PAD": nova PRIMEIRA opção da barra, um quadrado com o texto "PAD".
   Tocar nela funciona como interruptor "desligar formato customizado":
   grava PREF_ICON_SHAPE vazia, e ThemeManager já cai sozinho no
   config_icon_mask do sistema (comportamento nativo do launcher — não
   precisou de nenhuma lógica nova de desenho de ícone, só de UI).
   Tocar em qualquer outro quadradinho volta a aplicar aquele formato
   (liga o customizado de novo).

3) Flag expandableLongPressMenu (painel de long-press em Compose): este
   script NÃO mexe nela. Usuário testou visualmente o painel Compose
   contra o ArrowPopup retângulo original e decidiu manter desligado
   (achou o Compose feio e menos animado) — a flag permanece como
   estiver no seu Flags.java local, sem ser tocada aqui.

Uso:
    cd /caminho/do/XaulinXsLauncher3
    python3 apply_icon_shape_pad_and_visibility_fix.py

Idempotente: pode rodar mais de uma vez sem duplicar nada.
"""
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path.cwd()

SWATCH_VIEW_PATH = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/icons/IconShapeSwatchView.kt"
SELECTOR_PREF_PATH = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/settings/IconShapeSelectorPreference.kt"
STRINGS_PATH = REPO_ROOT / "res/values/xaulinxs_strings.xml"

MARKER_SWATCH = 'PAD_LABEL = "PAD"'
MARKER_SELECTOR = 'KEY_PAD = "__xaulinxs_pad_original__"'
MARKER_STRING = "xaulinxs_icon_shape_pad_description"

NEW_SWATCH_VIEW = r'''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Quadradinho selecionável que desenha o formato REAL de um
 * IconShapeModel (mesmo pathString usado por ThemeManager pra recortar
 * os ícones de verdade) — não é um ícone decorativo aproximado, é o
 * mesmo contorno vetorial que o launcher aplica quando esse shape é
 * escolhido. O path SVG-like de ShapesProvider usa um viewport 0-100;
 * aqui ele é escalado pro tamanho real da view via Matrix.
 *
 * XaulinXs fix (formatos "invisíveis" até tocar): antes, o contorno
 * (strokePaint) só era desenhado quando isSwatchSelected == true — os
 * quadradinhos não selecionados ficavam só com o preenchimento cinza
 * (fillColor = textColorSecondary), sem nenhuma borda, quase se
 * perdendo contra o fundo da tela de configurações até o usuário
 * tocar. Agora todo swatch sempre desenha um contorno sutil (idleStroke),
 * e o selecionado ganha, além do contorno de destaque mais grosso, um
 * preenchimento de fundo diferenciado (selectedFillColor) — dá pra ver
 * os 5 formatos de cara, sem precisar tocar em nenhum.
 *
 * XaulinXs feature (opção "PAD"): quando [isPadOption] é true, a view
 * ignora [shape] e desenha um quadrado simples com o texto "PAD" no
 * centro em vez de um contorno de IconShapeModel — representa "usar o
 * formato original do ícone do sistema" (ver
 * IconShapeSelectorPreference, que trata essa opção como limpar
 * ThemeManager.PREF_ICON_SHAPE em vez de gravar uma key de shape).
 */
package com.xaulinxs.customizations.icons

import android.content.Context
import android.graphics.Canvas
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.util.AttributeSet
import android.view.View
import androidx.core.graphics.PathParser
import com.android.launcher3.shapes.IconShapeModel

private const val PATH_VIEWPORT_SIZE = 100f
private const val PAD_LABEL = "PAD"
private const val PAD_CORNER_RADIUS_RATIO = 0.16f

/**
 * Desenha [shape] preenchido, com um contorno de seleção quando [isSelected]
 * é true. Clique/seleção são tratados pelo container (a barra), esta view só
 * desenha e expõe [isSelected] como estado visual.
 */
class IconShapeSwatchView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {

    private val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.FILL }
    private val idleStrokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE }
    private val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE }
    private val padLabelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        textAlign = Paint.Align.CENTER
        isFakeBoldText = true
        textSize = 14f * context.resources.displayMetrics.scaledDensity
    }
    private val padBackgroundPath = Path()
    private val rawPath = Path()
    private val scaledPath = Path()
    private val matrix = Matrix()

    /**
     * Quando true, esta view representa a opção "PAD" (formato original do
     * sistema) em vez de um IconShapeModel real — desenha um quadrado com o
     * texto "PAD" no centro, ignorando [shape].
     */
    var isPadOption: Boolean = false
        set(value) {
            field = value
            updateScaledPath()
            invalidate()
        }

    var shape: IconShapeModel? = null
        set(value) {
            field = value
            rawPath.reset()
            value?.let { runCatching { rawPath.set(PathParser.createPathFromPathData(it.pathString)) } }
            updateScaledPath()
            invalidate()
        }

    var fillColor: Int = 0
        set(value) {
            field = value
            fillPaint.color = value
            invalidate()
        }

    /** Cor do preenchimento quando este swatch está selecionado (fundo diferenciado). */
    var selectedFillColor: Int = 0
        set(value) {
            field = value
            invalidate()
        }

    /** Contorno sutil sempre visível, mesmo sem seleção — resolve a "invisibilidade" dos formatos. */
    var idleStrokeColor: Int = 0
        set(value) {
            field = value
            idleStrokePaint.color = value
            invalidate()
        }

    var strokeColor: Int = 0
        set(value) {
            field = value
            strokePaint.color = value
            padLabelPaint.color = value
            invalidate()
        }

    var strokeWidthPx: Float = 0f
        set(value) {
            field = value
            strokePaint.strokeWidth = value
            idleStrokePaint.strokeWidth = value.coerceAtLeast(1f) / 2f
            updateScaledPath()
            invalidate()
        }

    var isSwatchSelected: Boolean = false
        set(value) {
            field = value
            invalidate()
        }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        updateScaledPath()
    }

    private fun updateScaledPath() {
        scaledPath.reset()
        padBackgroundPath.reset()
        if (width <= 0 || height <= 0) return
        val inset = strokeWidthPx.coerceAtLeast(1f) * 2f

        if (isPadOption) {
            val radius = (width.coerceAtMost(height)) * PAD_CORNER_RADIUS_RATIO
            padBackgroundPath.addRoundRect(
                RectF(inset, inset, width - inset, height - inset),
                radius,
                radius,
                Path.Direction.CW,
            )
            return
        }

        if (rawPath.isEmpty) return
        // Encolhe um pouco o viewport pra sobrar espaço pro stroke de
        // seleção não ser cortado nas bordas da view.
        val target = RectF(inset, inset, width - inset, height - inset)
        matrix.reset()
        matrix.setRectToRect(
            RectF(0f, 0f, PATH_VIEWPORT_SIZE, PATH_VIEWPORT_SIZE),
            target,
            Matrix.ScaleToFit.CENTER,
        )
        rawPath.transform(matrix, scaledPath)
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val path = if (isPadOption) padBackgroundPath else scaledPath
        if (path.isEmpty) return

        fillPaint.color = if (isSwatchSelected && selectedFillColor != 0) selectedFillColor else fillColor
        canvas.drawPath(path, fillPaint)
        // Contorno sutil sempre desenhado (formato nunca fica "invisível"),
        // contorno de destaque desenhado por cima quando selecionado.
        canvas.drawPath(path, idleStrokePaint)
        if (isSwatchSelected) {
            canvas.drawPath(path, strokePaint)
        }

        if (isPadOption) {
            val textY = height / 2f - (padLabelPaint.descent() + padLabelPaint.ascent()) / 2f
            canvas.drawText(PAD_LABEL, width / 2f, textY, padLabelPaint)
        }
    }
}
'''

NEW_SELECTOR_PREF = r'''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Barra de quadradinhos selecionáveis (um por vez) com o formato REAL de
 * cada IconShapeModel disponível em ShapesProvider — a lista muda sozinha
 * conforme Flags.enableLauncherIconShapes(): com a flag ligada, ganha os
 * 5 formatos (círculo/quadrado/cookie 4/cookie 7/arco) que o próprio AOSP
 * já implementa via ThemeManager; com a flag desligada, sobra só círculo.
 *
 * XaulinXs feature (opção "PAD" = interruptor de formato customizado):
 * a PRIMEIRA opção da barra não é um IconShapeModel — é um quadrado com
 * o texto "PAD", representando "formato original do ícone do sistema".
 * Selecioná-la equivale a LIMPAR ThemeManager.PREF_ICON_SHAPE (string
 * vazia), e não a escrever uma key de shape. Isso funciona porque
 * ThemeManager.parseIconState() já trata esse caso sozinho: quando o
 * valor salvo não bate com nenhuma key em ShapesProvider.iconShapes
 * (shapeModel == null), ele cai automaticamente no config_icon_mask do
 * próprio sistema em vez de aplicar qualquer path customizado — ou
 * seja, "PAD" é o comportamento nativo do launcher, sem precisar de
 * nenhuma lógica nova de desenho de ícone aqui, só de UI. Isso funciona
 * como o interruptor pedido: tocar em PAD = desligar formato
 * customizado; tocar em qualquer outro quadradinho = ligar de volta
 * com aquele formato.
 *
 * O resto da lógica de aplicação continua igual: escreve a key
 * escolhida direto em ThemeManager.PREF_ICON_SHAPE (LauncherPrefs), que
 * o próprio ThemeManager já escuta (verifyIconState() via
 * LauncherPrefChangeListener) e propaga pra workspace/gaveta de apps
 * sozinho.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.graphics.Color
import android.util.AttributeSet
import android.util.TypedValue
import android.widget.LinearLayout
import androidx.preference.Preference
import androidx.preference.PreferenceViewHolder
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.R
import com.android.launcher3.graphics.ThemeManager
import com.android.launcher3.shapes.ShapesProvider
import com.xaulinxs.customizations.icons.IconShapeSwatchView

/** Key reservada pra opção "PAD" — nunca é gravada em PREF_ICON_SHAPE (ver KEY_PAD_CLEAR abaixo). */
private const val KEY_PAD = "__xaulinxs_pad_original__"

/** O que de fato gravamos em PREF_ICON_SHAPE ao escolher "PAD": string vazia = limpar/padrão. */
private const val KEY_PAD_CLEAR = ""

class IconShapeSelectorPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : Preference(context, attrs) {

    private val swatchSizePx = (48 * context.resources.displayMetrics.density).toInt()
    private val swatchGapPx = (12 * context.resources.displayMetrics.density).toInt()
    private val strokeWidthPx = 2.5f * context.resources.displayMetrics.density

    init {
        isPersistent = false
        isSelectable = false
        layoutResource = R.layout.xaulinxs_icon_shape_selector
    }

    override fun onBindViewHolder(holder: PreferenceViewHolder) {
        super.onBindViewHolder(holder)
        val container = holder.itemView.findViewById<LinearLayout>(
            R.id.xaulinxs_icon_shape_row
        )
        container.removeAllViews()

        val shapes = ShapesProvider.iconShapes
        val storedKey = LauncherPrefs.get(context).get(ThemeManager.PREF_ICON_SHAPE)
        val neutralFill = resolveNeutralFillColor()
        val selectedFill = resolveSelectedFillColor()
        val idleStroke = resolveIdleStrokeColor()
        val accentStroke = resolveAccentStrokeColor()
        val swatches = mutableListOf<Pair<IconShapeSwatchView, String>>()

        // "PAD" é sempre o primeiro item da barra, representando "formato
        // original do sistema" — selecionado sempre que PREF_ICON_SHAPE
        // estiver vazia (nenhum shape customizado escolhido ainda, ou
        // usuário tocou em PAD anteriormente pra desligar o customizado).
        val padSwatch = IconShapeSwatchView(context).apply {
            layoutParams = LinearLayout.LayoutParams(swatchSizePx, swatchSizePx).apply {
                marginEnd = swatchGapPx
            }
            isPadOption = true
            fillColor = neutralFill
            selectedFillColor = selectedFill
            idleStrokeColor = idleStroke
            strokeColor = accentStroke
            this.strokeWidthPx = this@IconShapeSelectorPreference.strokeWidthPx
            contentDescription = context.getString(R.string.xaulinxs_icon_shape_pad_description)
            isSwatchSelected = storedKey.isEmpty()
        }
        swatches += padSwatch to KEY_PAD
        container.addView(padSwatch)

        shapes.forEach { shapeModel ->
            val swatch = IconShapeSwatchView(context).apply {
                layoutParams = LinearLayout.LayoutParams(swatchSizePx, swatchSizePx).apply {
                    marginEnd = swatchGapPx
                }
                shape = shapeModel
                fillColor = neutralFill
                selectedFillColor = selectedFill
                idleStrokeColor = idleStroke
                strokeColor = accentStroke
                this.strokeWidthPx = this@IconShapeSelectorPreference.strokeWidthPx
                contentDescription = context.getString(shapeModel.titleId)
                // Com PAD como primeira opção, um shapeModel só é o
                // selecionado quando a key salva bater exatamente com ele
                // — chave vazia agora sempre significa PAD, nunca mais o
                // primeiro shape da lista por padrão.
                isSwatchSelected = storedKey == shapeModel.key
            }
            swatches += swatch to shapeModel.key
            container.addView(swatch)
        }

        swatches.forEach { (swatch, key) ->
            swatch.setOnClickListener {
                val valueToStore = if (key == KEY_PAD) KEY_PAD_CLEAR else key
                LauncherPrefs.get(context).put(ThemeManager.PREF_ICON_SHAPE, valueToStore)
                swatches.forEach { (s, k) -> s.isSwatchSelected = (k == key) }
            }
        }
    }

    private fun resolveNeutralFillColor(): Int {
        val typedValue = TypedValue()
        return if (context.theme.resolveAttribute(
                android.R.attr.colorBackgroundFloating, typedValue, true
            )
        ) {
            typedValue.data
        } else {
            Color.DKGRAY
        }
    }

    private fun resolveSelectedFillColor(): Int {
        val typedValue = TypedValue()
        return if (context.theme.resolveAttribute(
                android.R.attr.colorAccent, typedValue, true
            )
        ) {
            // Fundo do selecionado usa a cor de destaque com transparência,
            // pra não ficar idêntico ao contorno de seleção (que usa a
            // mesma cor sólida).
            Color.argb(60, Color.red(typedValue.data), Color.green(typedValue.data), Color.blue(typedValue.data))
        } else {
            Color.argb(60, 255, 255, 255)
        }
    }

    private fun resolveIdleStrokeColor(): Int {
        val typedValue = TypedValue()
        return if (context.theme.resolveAttribute(
                android.R.attr.textColorSecondary, typedValue, true
            )
        ) {
            typedValue.data
        } else {
            Color.GRAY
        }
    }

    private fun resolveAccentStrokeColor(): Int {
        val typedValue = TypedValue()
        return if (context.theme.resolveAttribute(
                android.R.attr.colorAccent, typedValue, true
            )
        ) {
            typedValue.data
        } else {
            Color.WHITE
        }
    }
}
'''

OLD_STRING_LINE = '    <string name="xaulinxs_icon_shape_summary">Toque num formato pra aplicar a todos os ícones e pastas. O primeiro (círculo) é o padrão</string>'
NEW_STRING_BLOCK = '''    <string name="xaulinxs_icon_shape_summary">Toque em PAD para usar o formato original do sistema, ou escolha um formato customizado para aplicar a todos os ícones e pastas</string>
    <!-- Descrição de acessibilidade do quadradinho "PAD" (primeira opção da
         barra de formatos) — não é um IconShapeModel, então não tem
         titleId próprio como os outros; ver IconShapeSelectorPreference. -->
    <string name="xaulinxs_icon_shape_pad_description">PAD: formato original do sistema (desativa o formato customizado)</string>'''


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def die(msg: str) -> None:
    print(f"ERRO: {msg}", file=sys.stderr)
    sys.exit(1)


def apply_full_rewrite(path: Path, marker: str, new_content: str, label: str) -> None:
    if not path.exists():
        die(f"{label}: arquivo não encontrado em {path}")
    current = path.read_text(encoding="utf-8")
    if marker in current:
        if sha256(current) == sha256(new_content):
            print(f"[OK] {label}: já aplicado, idêntico (pulando)")
        else:
            print(f"[AVISO] {label}: marcador já presente mas conteúdo difere do esperado — "
                  f"pulando por segurança (pode já ter sido editado manualmente). "
                  f"Se quiser forçar, apague o arquivo e rode de novo.")
        return
    path.write_text(new_content, encoding="utf-8")
    print(f"[APLICADO] {label}: reescrito ({path})")


def apply_strings_patch() -> None:
    if not STRINGS_PATH.exists():
        die(f"strings: arquivo não encontrado em {STRINGS_PATH}")
    current = STRINGS_PATH.read_text(encoding="utf-8")
    if MARKER_STRING in current:
        print("[OK] strings: já aplicado (pulando)")
        return
    if OLD_STRING_LINE not in current:
        die("strings: linha original de xaulinxs_icon_shape_summary não encontrada — "
            "arquivo pode já ter sido editado manualmente. Abortando esta etapa.")
    updated = current.replace(OLD_STRING_LINE, NEW_STRING_BLOCK)
    STRINGS_PATH.write_text(updated, encoding="utf-8")
    print(f"[APLICADO] strings: nova string PAD adicionada ({STRINGS_PATH})")


def main() -> None:
    print(f"Rodando em: {REPO_ROOT}")
    if not (REPO_ROOT / "aosp-stubs").exists():
        die("Este script deve ser rodado na RAIZ do repo XaulinXsLauncher3 "
            "(pasta aosp-stubs/ não encontrada aqui).")

    apply_full_rewrite(SWATCH_VIEW_PATH, MARKER_SWATCH, NEW_SWATCH_VIEW, "IconShapeSwatchView.kt")
    apply_full_rewrite(SELECTOR_PREF_PATH, MARKER_SELECTOR, NEW_SELECTOR_PREF, "IconShapeSelectorPreference.kt")
    apply_strings_patch()

    print("\nConcluído. Agora compile com:")
    print("  ./gradlew assembleNoQuickstepDebug")


if __name__ == "__main__":
    main()
