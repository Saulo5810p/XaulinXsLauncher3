/*
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
