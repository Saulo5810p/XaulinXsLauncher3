/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * "UI-UX Custom Colors" — tela dedicada com 2 sliders (Primária,
 * Secundária). Segue o mesmo padrão de layout hex+preview usado em
 * ManualColorPickerPreference, mas como Activity própria (não diálogo),
 * porque o usuário pediu um título/tela dedicados, não misturado na
 * feature de "cor manual" já existente (que é uma coisa diferente:
 * troca a cor-base dos ícones temáticos/scrim, não os materialColorX
 * usados em todo o app).
 *
 * Usa android.app.AlertDialog/View puro, não Compose nem AppCompat —
 * mesma razão documentada em ManualColorPickerPreference: a tela de
 * Settings herda de um tema puro do Android, sem Theme.AppCompat.
 */
package com.xaulinxs.customizations.settings

import android.app.Activity
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
import android.widget.ScrollView
import android.widget.SeekBar
import android.widget.TextView
import com.xaulinxs.customizations.theme.XaulinXsThemeColorResources
import com.xaulinxs.customizations.theme.XaulinXsThemedContextWrapper

class CustomColorsActivity : Activity() {

    // Mesmo motivo documentado em Launcher.attachBaseContext e
    // SettingsActivity.attachBaseContext: sem isso, esta própria tela não
    // refletiria a paleta já aplicada ao abrir (ex.: reabrir para ajustar).
    override fun attachBaseContext(base: Context) {
        super.attachBaseContext(XaulinXsThemedContextWrapper(base))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val density = resources.displayMetrics.density
        fun dp(v: Int) = (v * density).toInt()

        val initialPrimary = XaulinXsThemeColorResources.getPrimarySeed(this)
        val initialSecondary = XaulinXsThemeColorResources.getSecondarySeed(this)

        var isSyncingPrimary = false
        var isSyncingSecondary = false

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(24), dp(24), dp(24), dp(24))
        }

        fun sectionTitle(text: String) = TextView(this).apply {
            this.text = text
            textSize = 14f
            setPadding(0, dp(16), 0, dp(4))
        }

        // --- Bloco Primária ---
        root.addView(TextView(this).apply {
            text = "UI-UX Custom Colors"
            textSize = 20f
            setPadding(0, 0, 0, dp(8))
        })
        root.addView(TextView(this).apply {
            text = "Substitui as cores do sistema (interruptores, botões, " +
                "retângulos = Primária; fundos e fontes = Secundária) em " +
                "todo o app. Aplica ao reiniciar o launcher."
            textSize = 13f
            setPadding(0, 0, 0, dp(8))
        })

        val primaryPreview = View(this).apply { setBackgroundColor(initialPrimary) }
        val primaryHexInput = EditText(this).apply {
            inputType = InputType.TYPE_CLASS_TEXT
            setText(String.format("#%06X", 0xFFFFFF and initialPrimary))
        }

        fun makeRgbSlider(label: String, initialValue: Int): Pair<LinearLayout, SeekBar> {
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
            }
            val labelView = TextView(this).apply {
                text = label
                layoutParams = LinearLayout.LayoutParams(dp(24), LinearLayout.LayoutParams.WRAP_CONTENT)
            }
            val seekBar = SeekBar(this).apply {
                max = 255
                progress = initialValue
                layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            }
            row.addView(labelView)
            row.addView(seekBar)
            return row to seekBar
        }

        root.addView(sectionTitle("Cor Primária (interruptores, botões, retângulos)"))
        root.addView(
            primaryPreview,
            LinearLayout.LayoutParams(dp(48), dp(48)).apply { bottomMargin = dp(4) },
        )
        val (pR, pRSeek) = makeRgbSlider("R", Color.red(initialPrimary))
        val (pG, pGSeek) = makeRgbSlider("G", Color.green(initialPrimary))
        val (pB, pBSeek) = makeRgbSlider("B", Color.blue(initialPrimary))
        root.addView(pR); root.addView(pG); root.addView(pB)
        root.addView(primaryHexInput)

        fun currentPrimary() = Color.rgb(pRSeek.progress, pGSeek.progress, pBSeek.progress)
        fun updatePrimaryFromSliders() {
            if (isSyncingPrimary) return
            isSyncingPrimary = true
            val color = currentPrimary()
            primaryPreview.setBackgroundColor(color)
            primaryHexInput.setText(String.format("#%06X", 0xFFFFFF and color))
            primaryHexInput.setSelection(primaryHexInput.text.length)
            isSyncingPrimary = false
        }
        val primarySliderListener = object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(sb: SeekBar?, progress: Int, fromUser: Boolean) {
                if (fromUser) updatePrimaryFromSliders()
            }
            override fun onStartTrackingTouch(sb: SeekBar?) {}
            override fun onStopTrackingTouch(sb: SeekBar?) {}
        }
        pRSeek.setOnSeekBarChangeListener(primarySliderListener)
        pGSeek.setOnSeekBarChangeListener(primarySliderListener)
        pBSeek.setOnSeekBarChangeListener(primarySliderListener)
        primaryHexInput.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun afterTextChanged(s: Editable?) {
                if (isSyncingPrimary) return
                val parsed = parseHexOrNull(s?.toString()) ?: return
                isSyncingPrimary = true
                primaryPreview.setBackgroundColor(parsed)
                pRSeek.progress = Color.red(parsed)
                pGSeek.progress = Color.green(parsed)
                pBSeek.progress = Color.blue(parsed)
                isSyncingPrimary = false
            }
        })

        // --- Bloco Secundária ---
        val secondaryPreview = View(this).apply { setBackgroundColor(initialSecondary) }
        val secondaryHexInput = EditText(this).apply {
            inputType = InputType.TYPE_CLASS_TEXT
            setText(String.format("#%06X", 0xFFFFFF and initialSecondary))
        }

        root.addView(sectionTitle("Cor Secundária (fundos/background, fontes)"))
        root.addView(
            secondaryPreview,
            LinearLayout.LayoutParams(dp(48), dp(48)).apply { bottomMargin = dp(4) },
        )
        val (sR, sRSeek) = makeRgbSlider("R", Color.red(initialSecondary))
        val (sG, sGSeek) = makeRgbSlider("G", Color.green(initialSecondary))
        val (sB, sBSeek) = makeRgbSlider("B", Color.blue(initialSecondary))
        root.addView(sR); root.addView(sG); root.addView(sB)
        root.addView(secondaryHexInput)

        fun currentSecondary() = Color.rgb(sRSeek.progress, sGSeek.progress, sBSeek.progress)
        fun updateSecondaryFromSliders() {
            if (isSyncingSecondary) return
            isSyncingSecondary = true
            val color = currentSecondary()
            secondaryPreview.setBackgroundColor(color)
            secondaryHexInput.setText(String.format("#%06X", 0xFFFFFF and color))
            secondaryHexInput.setSelection(secondaryHexInput.text.length)
            isSyncingSecondary = false
        }
        val secondarySliderListener = object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(sb: SeekBar?, progress: Int, fromUser: Boolean) {
                if (fromUser) updateSecondaryFromSliders()
            }
            override fun onStartTrackingTouch(sb: SeekBar?) {}
            override fun onStopTrackingTouch(sb: SeekBar?) {}
        }
        sRSeek.setOnSeekBarChangeListener(secondarySliderListener)
        sGSeek.setOnSeekBarChangeListener(secondarySliderListener)
        sBSeek.setOnSeekBarChangeListener(secondarySliderListener)
        secondaryHexInput.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun afterTextChanged(s: Editable?) {
                if (isSyncingSecondary) return
                val parsed = parseHexOrNull(s?.toString()) ?: return
                isSyncingSecondary = true
                secondaryPreview.setBackgroundColor(parsed)
                sRSeek.progress = Color.red(parsed)
                sGSeek.progress = Color.green(parsed)
                sBSeek.progress = Color.blue(parsed)
                isSyncingSecondary = false
            }
        })

        // --- Botões ---
        val buttonRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.END
            setPadding(0, dp(24), 0, 0)
        }
        val disableButton = Button(this).apply {
            text = "Desativar (usar padrão)"
            setOnClickListener {
                XaulinXsThemeColorResources.setEnabled(this@CustomColorsActivity, false)
                recreate()
            }
        }
        val saveButton = Button(this).apply {
            text = "Aplicar"
            setOnClickListener {
                XaulinXsThemeColorResources.applyAndSave(
                    this@CustomColorsActivity,
                    currentPrimary() or -0x1000000,
                    currentSecondary() or -0x1000000,
                )
                recreate()
            }
        }
        buttonRow.addView(disableButton)
        buttonRow.addView(saveButton)
        root.addView(buttonRow)

        setContentView(ScrollView(this).apply { addView(root) })
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
