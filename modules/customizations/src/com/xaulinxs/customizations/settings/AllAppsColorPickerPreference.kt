/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Editor de cor manual do Menu de aplicativo: paleta de swatches rápidos +
 * campo hex + 3 sliders RGB, todos sincronizados entre si, com preview ao
 * vivo dentro do próprio diálogo. Mesmo padrão de hex+RGB já usado por
 * ManualColorPickerPreference (ícones)/BalloonColorPickerPreference
 * (balões)/FolderColorPickerPreference (pastas), com paleta adicionada por
 * pedido explícito do usuário para esta feature.
 *
 * Usa android.app.AlertDialog (framework), não androidx.appcompat — a tela
 * de Settings (HomeSettings.Theme) herda de um tema puro do Android, não um
 * Theme.AppCompat. AlertDialog do AppCompat exige um tema AppCompat e
 * crasha (IllegalStateException) nesse contexto.
 */
package com.xaulinxs.customizations.settings

import android.app.AlertDialog
import android.content.Context
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.text.Editable
import android.text.InputType
import android.text.TextWatcher
import android.util.AttributeSet
import android.view.Gravity
import android.view.View
import android.widget.EditText
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.SeekBar
import android.widget.TextView
import androidx.preference.Preference
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.R
import com.xaulinxs.customizations.theme.XaulinXsAllAppsColor

class AllAppsColorPickerPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : Preference(context, attrs) {

    init {
        isPersistent = false
        updateSummary()
    }

    override fun onClick() {
        val prefs = LauncherPrefs.get(context)
        val currentColor = prefs.get(XaulinXsAllAppsColor.ALLAPPS_COLOR_ARGB)
        val density = context.resources.displayMetrics.density
        val previewSizePx = (56 * density).toInt()
        val paddingPx = (24 * density).toInt()
        val swatchSizePx = (40 * density).toInt()
        val swatchMarginPx = (8 * density).toInt()

        var isSyncing = false

        val preview = View(context).apply { setBackgroundColor(currentColor) }

        val hexInput = EditText(context).apply {
            inputType = InputType.TYPE_CLASS_TEXT
            setText(String.format("#%06X", 0xFFFFFF and currentColor))
            setSelection(text.length)
        }

        fun makeSlider(label: String, initialValue: Int): Pair<LinearLayout, SeekBar> {
            val row = LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
            }
            val labelView = TextView(context).apply {
                text = label
                val labelWidth = (24 * density).toInt()
                layoutParams = LinearLayout.LayoutParams(labelWidth, LinearLayout.LayoutParams.WRAP_CONTENT)
            }
            val seekBar = SeekBar(context).apply {
                max = 255
                progress = initialValue
                layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            }
            row.addView(labelView)
            row.addView(seekBar)
            return row to seekBar
        }

        val (redRow, redSeek) = makeSlider("R", Color.red(currentColor))
        val (greenRow, greenSeek) = makeSlider("G", Color.green(currentColor))
        val (blueRow, blueSeek) = makeSlider("B", Color.blue(currentColor))

        fun currentSliderColor(): Int =
            Color.rgb(redSeek.progress, greenSeek.progress, blueSeek.progress)

        fun updateFromColor(color: Int) {
            isSyncing = true
            preview.setBackgroundColor(color)
            hexInput.setText(String.format("#%06X", 0xFFFFFF and color))
            hexInput.setSelection(hexInput.text.length)
            redSeek.progress = Color.red(color)
            greenSeek.progress = Color.green(color)
            blueSeek.progress = Color.blue(color)
            isSyncing = false
        }

        fun updateFromSliders() {
            if (isSyncing) return
            isSyncing = true
            val color = currentSliderColor()
            preview.setBackgroundColor(color)
            hexInput.setText(String.format("#%06X", 0xFFFFFF and color))
            hexInput.setSelection(hexInput.text.length)
            isSyncing = false
        }

        val sliderListener = object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                if (fromUser) updateFromSliders()
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        }
        redSeek.setOnSeekBarChangeListener(sliderListener)
        greenSeek.setOnSeekBarChangeListener(sliderListener)
        blueSeek.setOnSeekBarChangeListener(sliderListener)

        hexInput.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun afterTextChanged(s: Editable?) {
                if (isSyncing) return
                val parsed = parseHexOrNull(s?.toString()) ?: return
                isSyncing = true
                preview.setBackgroundColor(parsed)
                redSeek.progress = Color.red(parsed)
                greenSeek.progress = Color.green(parsed)
                blueSeek.progress = Color.blue(parsed)
                isSyncing = false
            }
        })

        // Paleta de swatches rápidos: linha horizontal roláve com cores
        // Material comuns + a cor atualmente selecionada em destaque
        // (borda mais grossa). Tocar um swatch aplica a cor na hora nos
        // outros dois controles (hex + sliders), sem fechar o diálogo —
        // o usuário ainda pode refinar com os sliders/hex depois.
        val paletteScroll = HorizontalScrollView(context).apply {
            isHorizontalScrollBarEnabled = false
        }
        val paletteRow = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
        }
        paletteScroll.addView(paletteRow)

        lateinit var refreshPaletteSelection: () -> Unit
        val swatchViews = mutableListOf<Pair<Int, View>>()

        for (swatchColor in XAULINXS_ALLAPPS_COLOR_PALETTE) {
            val swatch = View(context).apply {
                background = GradientDrawable().apply {
                    shape = GradientDrawable.OVAL
                    setColor(swatchColor)
                    setStroke((2 * density).toInt(), Color.argb(60, 0, 0, 0))
                }
                layoutParams = LinearLayout.LayoutParams(swatchSizePx, swatchSizePx).apply {
                    marginEnd = swatchMarginPx
                }
                setOnClickListener {
                    updateFromColor(swatchColor)
                    refreshPaletteSelection()
                }
            }
            swatchViews += swatchColor to swatch
            paletteRow.addView(swatch)
        }

        refreshPaletteSelection = {
            val selected = currentSliderColor()
            for ((swatchColor, swatchView) in swatchViews) {
                val isSelected = swatchColor == selected
                (swatchView.background as GradientDrawable).setStroke(
                    ((if (isSelected) 4 else 2) * density).toInt(),
                    if (isSelected) selected else Color.argb(60, 0, 0, 0),
                )
            }
        }

        refreshPaletteSelection()

        val container = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(paddingPx, paddingPx, paddingPx, paddingPx)
            addView(
                preview,
                LinearLayout.LayoutParams(previewSizePx, previewSizePx).apply {
                    gravity = Gravity.CENTER_HORIZONTAL
                    bottomMargin = paddingPx / 2
                },
            )
            addView(
                paletteScroll,
                LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                ).apply { bottomMargin = paddingPx / 2 },
            )
            addView(redRow)
            addView(greenRow)
            addView(blueRow)
            addView(hexInput)
        }

        AlertDialog.Builder(context)
            .setTitle(R.string.xaulinxs_allapps_color_picker_title)
            .setView(container)
            .setPositiveButton(R.string.xaulinxs_manual_color_save) { _, _ ->
                val parsed = parseHexOrNull(hexInput.text?.toString()) ?: currentSliderColor()
                prefs.put(XaulinXsAllAppsColor.ALLAPPS_COLOR_ARGB, parsed or -0x1000000)
                updateSummary()
                com.xaulinxs.customizations.theme.XaulinXsAllAppsTransparencyRedraw.requestRedraw(context)
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun updateSummary() {
        val color = LauncherPrefs.get(context).get(XaulinXsAllAppsColor.ALLAPPS_COLOR_ARGB)
        summary = String.format("#%06X", 0xFFFFFF and color)
    }

    private fun parseHexOrNull(input: String?): Int? {
        if (input.isNullOrBlank()) return null
        val clean = input.removePrefix("#").trim()
        if (clean.length != 6 && clean.length != 8) return null
        return try {
            val argb = if (clean.length == 6) "FF$clean" else clean
            (argb.toLong(16) and 0xFFFFFFFFL).toInt()
        } catch (e: NumberFormatException) {
            null
        }
    }

    companion object {
        // Paleta fixa de cores Material comuns (tons 400-700, já ARGB
        // opacos) para seleção rápida — não depende de wallpaper/Monet,
        // já que esta feature existe justamente para o caso de o usuário
        // querer uma cor fixa própria.
        private val XAULINXS_ALLAPPS_COLOR_PALETTE = intArrayOf(
            0xFFE53935.toInt(), // vermelho
            0xFFD81B60.toInt(), // rosa
            0xFF8E24AA.toInt(), // roxo
            0xFF5E35B1.toInt(), // roxo profundo
            0xFF3949AB.toInt(), // índigo
            0xFF1E88E5.toInt(), // azul
            0xFF00897B.toInt(), // verde-azulado
            0xFF43A047.toInt(), // verde
            0xFFFDD835.toInt(), // amarelo
            0xFFFB8C00.toInt(), // laranja
            0xFF6D4C41.toInt(), // marrom
            0xFF546E7A.toInt(), // azul acinzentado
            0xFF000000.toInt(), // preto
            0xFFFFFFFF.toInt(), // branco
        )
    }
}

// XAULINXS_ALLAPPS_COLOR_PICKER_PREFERENCE_FILE
