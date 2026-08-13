/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Seletor de cor em hex (#RRGGBB ou #AARRGGBB) com preview ao vivo, num
 * AlertDialog simples (androidx.appcompat, já é dependência do projeto).
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.text.Editable
import android.text.InputType
import android.text.TextWatcher
import android.util.AttributeSet
import android.view.Gravity
import android.view.View
import android.widget.EditText
import android.widget.LinearLayout
import android.app.AlertDialog
import androidx.preference.Preference
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.R
import com.xaulinxs.customizations.search.XaulinXsSearchBarPrefs

class SearchBarColorPickerPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : Preference(context, attrs) {

    init {
        isPersistent = false
        updateSummary()
    }

    override fun onClick() {
        val prefs = LauncherPrefs.get(context)
        val currentColor = prefs.get(XaulinXsSearchBarPrefs.SEARCH_BAR_CUSTOM_COLOR_VALUE)
        val density = context.resources.displayMetrics.density
        val previewSizePx = (56 * density).toInt()
        val paddingPx = (24 * density).toInt()

        val preview = View(context).apply { setBackgroundColor(currentColor) }

        val hexInput = EditText(context).apply {
            inputType = InputType.TYPE_CLASS_TEXT
            setText(String.format("#%06X", 0xFFFFFF and currentColor))
            setSelection(text.length)
            addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
                override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
                override fun afterTextChanged(s: Editable?) {
                    parseHexOrNull(s?.toString())?.let { preview.setBackgroundColor(it) }
                }
            })
        }

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
            addView(hexInput)
        }

        AlertDialog.Builder(context)
            .setTitle(R.string.xaulinxs_searchbar_color_picker_title)
            .setView(container)
            .setPositiveButton(android.R.string.ok) { _, _ ->
                val parsed = parseHexOrNull(hexInput.text?.toString()) ?: currentColor
                prefs.put(XaulinXsSearchBarPrefs.SEARCH_BAR_CUSTOM_COLOR_VALUE, parsed)
                updateSummary()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun updateSummary() {
        val color = LauncherPrefs.get(context).get(XaulinXsSearchBarPrefs.SEARCH_BAR_CUSTOM_COLOR_VALUE)
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
