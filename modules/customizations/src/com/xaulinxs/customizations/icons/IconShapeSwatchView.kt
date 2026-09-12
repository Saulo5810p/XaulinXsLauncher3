/*
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
