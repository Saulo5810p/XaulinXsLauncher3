/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Quadradinho selecionável que desenha o formato REAL de um
 * IconShapeModel (mesmo pathString usado por ThemeManager pra recortar
 * os ícones de verdade) — não é um ícone decorativo aproximado, é o
 * mesmo contorno vetorial que o launcher aplica quando esse shape é
 * escolhido. O path SVG-like de ShapesProvider usa um viewport 0-100;
 * aqui ele é escalado pro tamanho real da view via Matrix.
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
    private val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE }
    private val rawPath = Path()
    private val scaledPath = Path()
    private val matrix = Matrix()

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

    var strokeColor: Int = 0
        set(value) {
            field = value
            strokePaint.color = value
            invalidate()
        }

    var strokeWidthPx: Float = 0f
        set(value) {
            field = value
            strokePaint.strokeWidth = value
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
        if (rawPath.isEmpty || width <= 0 || height <= 0) return
        // Encolhe um pouco o viewport pra sobrar espaço pro stroke de
        // seleção não ser cortado nas bordas da view.
        val inset = strokeWidthPx.coerceAtLeast(1f) * 2f
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
        if (scaledPath.isEmpty) return
        canvas.drawPath(scaledPath, fillPaint)
        if (isSwatchSelected) {
            canvas.drawPath(scaledPath, strokePaint)
        }
    }
}
