/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Editor de cor manual: campo hex + 3 sliders RGB, sincronizados entre si,
 * com preview ao vivo dentro do próprio diálogo.
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
import android.text.Editable
import android.text.InputType
import android.text.TextWatcher
import android.util.AttributeSet
import android.view.Gravity
import android.view.View
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.SeekBar
import android.widget.TextView
import androidx.preference.Preference
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.R
import com.xaulinxs.customizations.theme.XaulinXsManualColor

class ManualColorPickerPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : Preference(context, attrs) {

    init {
        isPersistent = false
        updateSummary()
    }

    override fun onClick() {
        val prefs = LauncherPrefs.get(context)
        val currentColor = prefs.get(XaulinXsManualColor.MANUAL_COLOR_VALUE)
        val density = context.resources.displayMetrics.density
        val previewSizePx = (56 * density).toInt()
        val paddingPx = (24 * density).toInt()

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
            addView(redRow)
            addView(greenRow)
            addView(blueRow)
            addView(hexInput)
        }

        AlertDialog.Builder(context)
            .setTitle(R.string.xaulinxs_manual_color_picker_title)
            .setView(container)
            .setPositiveButton(R.string.xaulinxs_manual_color_save) { _, _ ->
                val parsed = parseHexOrNull(hexInput.text?.toString()) ?: currentSliderColor()
                prefs.put(XaulinXsManualColor.MANUAL_COLOR_VALUE, parsed or -0x1000000)
                updateSummary()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun updateSummary() {
        val color = LauncherPrefs.get(context).get(XaulinXsManualColor.MANUAL_COLOR_VALUE)
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
}
