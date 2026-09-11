/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Barra de quadradinhos selecionáveis (um por vez) com o formato REAL de
 * cada IconShapeModel disponível em ShapesProvider — a lista muda sozinha
 * conforme Flags.enableLauncherIconShapes(): com a flag ligada, ganha os
 * 5 formatos (círculo/quadrado/cookie 4/cookie 7/arco) que o próprio AOSP
 * já implementa via ThemeManager; com a flag desligada, sobra só círculo.
 *
 * Não existe lógica de aplicação de formato aqui: escreve a key escolhida
 * direto em ThemeManager.PREF_ICON_SHAPE (LauncherPrefs), que o próprio
 * ThemeManager já escuta (verifyIconState() via LauncherPrefChangeListener)
 * e propaga pra workspace/gaveta de apps sozinho. String vazia = padrão
 * (comportamento idêntico a nunca ter mexido nessa preference).
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
        val swatches = mutableListOf<Pair<IconShapeSwatchView, String>>()

        shapes.forEach { shapeModel ->
            val swatch = IconShapeSwatchView(context).apply {
                layoutParams = LinearLayout.LayoutParams(swatchSizePx, swatchSizePx).apply {
                    marginEnd = swatchGapPx
                }
                shape = shapeModel
                fillColor = resolveNeutralFillColor()
                strokeColor = resolveAccentStrokeColor()
                this.strokeWidthPx = this@IconShapeSelectorPreference.strokeWidthPx
                contentDescription = context.getString(shapeModel.titleId)
                // Chave vazia = padrão: representamos isso selecionando o
                // primeiro shape da lista (círculo, sempre índice 0, com a
                // flag ligada ou desligada), pra sempre existir exatamente
                // um quadradinho marcado, mesmo antes de qualquer toque.
                isSwatchSelected = storedKey == shapeModel.key ||
                    (storedKey.isEmpty() && shapeModel === shapes.first())
            }
            swatches += swatch to shapeModel.key
            container.addView(swatch)
        }

        swatches.forEach { (swatch, key) ->
            swatch.setOnClickListener {
                LauncherPrefs.get(context).put(ThemeManager.PREF_ICON_SHAPE, key)
                swatches.forEach { (s, k) -> s.isSwatchSelected = (k == key) }
            }
        }
    }

    private fun resolveNeutralFillColor(): Int {
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
