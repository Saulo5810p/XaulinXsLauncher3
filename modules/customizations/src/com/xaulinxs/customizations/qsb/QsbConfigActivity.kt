/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Tela dedicada de configuração da QSB. Aberta de duas formas, ambas
 * exigidas: (1) balão do long-press na QSB da home — mesmo padrão que o
 * widget de busca do Google usava antes dos fixes de estabilidade desta
 * linha de trabalho, ver OseWidgetOptionsProvider —, e (2) entrada
 * dentro de "XaulinXs Customizations" nas Settings do launcher, ver
 * launcher_preferences.xml.
 *
 * Activity pura (não PreferenceScreen), single screen: 4 sliders
 * (Tamanho/Largura/Transparência/Cor) + 2 modos mutuamente exclusivos
 * (Web/Texto) via RadioGroup. Segue o mesmo padrão de Activity simples
 * (sem AppCompat) usado por XaulinXsFontFileManagerActivity — a tela de
 * Settings usa HomeSettings.Theme, que herda de um tema puro do
 * Android, não Theme.AppCompat.
 *
 * O editor de cor (hex + RGB sincronizados) é o mesmo diálogo usado por
 * ManualColorPickerPreference — mesma UI, agora persistindo em
 * QsbConfig.BAR_COLOR em vez de XaulinXsManualColor.MANUAL_COLOR_VALUE.
 */
package com.xaulinxs.customizations.qsb

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.graphics.Color
import android.os.Bundle
import android.text.Editable
import android.text.InputType
import android.text.TextWatcher
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.RadioGroup
import android.widget.SeekBar
import android.widget.TextView
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.R

class QsbConfigActivity : Activity() {

    private lateinit var sizeLabel: TextView
    private lateinit var sizeSeekBar: SeekBar
    private lateinit var widthLabel: TextView
    private lateinit var widthSeekBar: SeekBar
    private lateinit var transparencyLabel: TextView
    private lateinit var transparencySeekBar: SeekBar
    private lateinit var colorPreview: View
    private lateinit var colorButton: Button
    private lateinit var modeRadioGroup: RadioGroup

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.xaulinxs_qsb_config_activity)
        setTitle(R.string.xaulinxs_qsb_config_title)

        val prefs = LauncherPrefs.get(this)

        sizeLabel = findViewById(R.id.xaulinxs_qsb_size_label)
        sizeSeekBar = findViewById(R.id.xaulinxs_qsb_size_seekbar)
        widthLabel = findViewById(R.id.xaulinxs_qsb_width_label)
        widthSeekBar = findViewById(R.id.xaulinxs_qsb_width_seekbar)
        transparencyLabel = findViewById(R.id.xaulinxs_qsb_transparency_label)
        transparencySeekBar = findViewById(R.id.xaulinxs_qsb_transparency_seekbar)
        colorPreview = findViewById(R.id.xaulinxs_qsb_color_preview)
        colorButton = findViewById(R.id.xaulinxs_qsb_color_button)
        modeRadioGroup = findViewById(R.id.xaulinxs_qsb_mode_radio_group)

        setUpSizeSlider(prefs)
        setUpWidthSlider(prefs)
        setUpTransparencySlider(prefs)
        setUpColorPicker(prefs)
        setUpModeRadioGroup(prefs)
    }

    private fun setUpSizeSlider(prefs: LauncherPrefs) {
        sizeSeekBar.max = QsbConfig.MAX_SIZE_PERCENT - QsbConfig.MIN_SIZE_PERCENT
        val current = prefs.get(QsbConfig.SIZE_PERCENT)
        sizeSeekBar.progress = current - QsbConfig.MIN_SIZE_PERCENT
        updateSizeLabel(current)
        sizeSeekBar.setOnSeekBarChangeListener(
            onChange { progress ->
                val percent = progress + QsbConfig.MIN_SIZE_PERCENT
                updateSizeLabel(percent)
                prefs.put(QsbConfig.SIZE_PERCENT to percent)
            }
        )
    }

    private fun setUpWidthSlider(prefs: LauncherPrefs) {
        widthSeekBar.max = QsbConfig.MAX_WIDTH_PERCENT - QsbConfig.MIN_WIDTH_PERCENT
        val current = prefs.get(QsbConfig.WIDTH_PERCENT)
        widthSeekBar.progress = current - QsbConfig.MIN_WIDTH_PERCENT
        updateWidthLabel(current)
        widthSeekBar.setOnSeekBarChangeListener(
            onChange { progress ->
                val percent = progress + QsbConfig.MIN_WIDTH_PERCENT
                updateWidthLabel(percent)
                prefs.put(QsbConfig.WIDTH_PERCENT to percent)
            }
        )
    }

    private fun setUpTransparencySlider(prefs: LauncherPrefs) {
        transparencySeekBar.max =
            QsbConfig.MAX_TRANSPARENCY_PERCENT - QsbConfig.MIN_TRANSPARENCY_PERCENT
        val current = prefs.get(QsbConfig.TRANSPARENCY_PERCENT)
        transparencySeekBar.progress = current - QsbConfig.MIN_TRANSPARENCY_PERCENT
        updateTransparencyLabel(current)
        transparencySeekBar.setOnSeekBarChangeListener(
            onChange { progress ->
                val percent = progress + QsbConfig.MIN_TRANSPARENCY_PERCENT
                updateTransparencyLabel(percent)
                prefs.put(QsbConfig.TRANSPARENCY_PERCENT to percent)
            }
        )
    }

    private fun setUpColorPicker(prefs: LauncherPrefs) {
        fun refreshPreview() {
            colorPreview.setBackgroundColor(prefs.get(QsbConfig.BAR_COLOR))
        }
        refreshPreview()
        colorButton.setOnClickListener { showColorPickerDialog(prefs) { refreshPreview() } }
    }

    private fun setUpModeRadioGroup(prefs: LauncherPrefs) {
        val checkedId =
            if (prefs.get(QsbConfig.MODE_TEXT_ENABLED)) {
                R.id.xaulinxs_qsb_mode_text
            } else {
                R.id.xaulinxs_qsb_mode_web
            }
        modeRadioGroup.check(checkedId)
        modeRadioGroup.setOnCheckedChangeListener { _, checkedButtonId ->
            prefs.put(QsbConfig.MODE_TEXT_ENABLED to (checkedButtonId == R.id.xaulinxs_qsb_mode_text))
        }
    }

    private fun updateSizeLabel(percent: Int) {
        sizeLabel.text = getString(R.string.xaulinxs_qsb_config_size_label, percent)
    }

    private fun updateWidthLabel(percent: Int) {
        widthLabel.text = getString(R.string.xaulinxs_qsb_config_width_label, percent)
    }

    private fun updateTransparencyLabel(percent: Int) {
        transparencyLabel.text = getString(R.string.xaulinxs_qsb_config_transparency_label, percent)
    }

    /**
     * Editor de cor (preview + 3 sliders RGB + campo hex), mesmo padrão
     * de ManualColorPickerPreference — reimplementado aqui em vez de
     * reaproveitado diretamente porque aquele é um androidx.preference.Preference
     * (precisa de PreferenceScreen hospedeira) e esta é uma Activity solta.
     */
    private fun showColorPickerDialog(prefs: LauncherPrefs, onSaved: () -> Unit) {
        val context: Context = this
        val currentColor = prefs.get(QsbConfig.BAR_COLOR)
        val density = context.resources.displayMetrics.density
        val previewSizePx = (56 * density).toInt()
        val paddingPx = (24 * density).toInt()

        var isSyncing = false

        val preview = View(context).apply { setBackgroundColor(currentColor) }

        val hexInput =
            EditText(context).apply {
                inputType = InputType.TYPE_CLASS_TEXT
                setText(String.format("#%06X", 0xFFFFFF and currentColor))
                setSelection(text.length)
            }

        fun makeSlider(label: String, initialValue: Int): Pair<LinearLayout, SeekBar> {
            val row =
                LinearLayout(context).apply {
                    orientation = LinearLayout.HORIZONTAL
                    gravity = Gravity.CENTER_VERTICAL
                }
            val labelView =
                TextView(context).apply {
                    text = label
                    val labelWidth = (24 * density).toInt()
                    layoutParams =
                        LinearLayout.LayoutParams(labelWidth, LinearLayout.LayoutParams.WRAP_CONTENT)
                }
            val seekBar =
                SeekBar(context).apply {
                    max = 255
                    progress = initialValue
                    layoutParams =
                        LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
                }
            row.addView(labelView)
            row.addView(seekBar)
            return row to seekBar
        }

        val (redRow, redSeek) = makeSlider("R", Color.red(currentColor))
        val (greenRow, greenSeek) = makeSlider("G", Color.green(currentColor))
        val (blueRow, blueSeek) = makeSlider("B", Color.blue(currentColor))

        fun currentSliderColor(): Int = Color.rgb(redSeek.progress, greenSeek.progress, blueSeek.progress)

        fun updateFromSliders() {
            if (isSyncing) return
            isSyncing = true
            val color = currentSliderColor()
            preview.setBackgroundColor(color)
            hexInput.setText(String.format("#%06X", 0xFFFFFF and color))
            hexInput.setSelection(hexInput.text.length)
            isSyncing = false
        }

        val sliderListener =
            object : SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                    if (fromUser) updateFromSliders()
                }
                override fun onStartTrackingTouch(seekBar: SeekBar?) {}
                override fun onStopTrackingTouch(seekBar: SeekBar?) {}
            }
        redSeek.setOnSeekBarChangeListener(sliderListener)
        greenSeek.setOnSeekBarChangeListener(sliderListener)
        blueSeek.setOnSeekBarChangeListener(sliderListener)

        hexInput.addTextChangedListener(
            object : TextWatcher {
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
            }
        )

        val container =
            LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(paddingPx, paddingPx, paddingPx, paddingPx)
                addView(
                    preview,
                    LinearLayout.LayoutParams(previewSizePx, previewSizePx).apply {
                        gravity = Gravity.CENTER_HORIZONTAL
                        bottomMargin = paddingPx / 2
                    },
                )
                addView(redRow)
                addView(greenRow)
                addView(blueRow)
                addView(hexInput)
            }

        AlertDialog.Builder(context)
            .setTitle(R.string.xaulinxs_qsb_config_color_picker_title)
            .setView(container)
            .setPositiveButton(R.string.xaulinxs_manual_color_save) { _, _ ->
                val parsed = parseHexOrNull(hexInput.text?.toString()) ?: currentSliderColor()
                prefs.put(QsbConfig.BAR_COLOR to (parsed or -0x1000000))
                onSaved()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
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

    private fun onChange(action: (Int) -> Unit): SeekBar.OnSeekBarChangeListener =
        object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                if (fromUser) action(progress)
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        }
}
