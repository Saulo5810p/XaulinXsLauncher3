"""
XaulinXs Customizations — Feature 5: Editor de cor manual (hex) para
ícones temáticos + fundo do App Drawer, com preview.
Idempotente: pode rodar quantas vezes quiser.
"""
from pathlib import Path

def write_if_absent(path_str, content):
    path = Path(path_str)
    if path.exists():
        print(f"SKIP (já existe): {path_str}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"CRIADO: {path_str}")

def replace_once(path_str, old, new, label):
    path = Path(path_str)
    assert path.exists(), f"arquivo não encontrado: {path_str}"
    content = path.read_text(encoding="utf-8")
    if new in content:
        print(f"SKIP ({label}): já aplicado")
        return
    assert old in content, f"âncora não encontrada em {path_str} ({label})"
    assert content.count(old) == 1, f"âncora aparece mais de uma vez em {path_str} ({label})"
    content = content.replace(old, new)
    path.write_text(content, encoding="utf-8")
    print(f"APLICADO: {label}")


write_if_absent(
    "modules/customizations/src/com/xaulinxs/customizations/theme/XaulinXsManualColor.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Fonte de cor manual (Feature 5). Quando ativada, esta cor fixa escolhida
 * pelo usuário substitui a cor extraída do wallpaper (WallpaperColorHints)
 * como cor-base tanto para os ícones temáticos (XaulinXsThemedIconColors)
 * quanto para o fundo/scrim do App Drawer (WallpaperScrimHelper) — os dois
 * continuam aplicando o mesmo sombreamento claro/escuro de sempre, só muda
 * de onde vem a cor de entrada.
 */
package com.xaulinxs.customizations.theme

import android.content.Context
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

object XaulinXsManualColor {

    private const val KEY_ENABLED = "xaulinxs_manual_color_enabled"
    private const val KEY_VALUE = "xaulinxs_manual_color_value"

    private const val DEFAULT_COLOR = 0xFF6750A4.toInt() // roxo Material, ARGB opaco

    val MANUAL_COLOR_ENABLED = backedUpItem(KEY_ENABLED, false)
    val MANUAL_COLOR_VALUE = backedUpItem(KEY_VALUE, DEFAULT_COLOR)

    /** Cor-base manual (ARGB opaco) se o modo estiver ativado, senão null. */
    @JvmStatic
    fun getBaseColorIfEnabled(context: Context): Int? {
        val prefs = LauncherPrefs.get(context)
        if (!prefs.get(MANUAL_COLOR_ENABLED)) return null
        return prefs.get(MANUAL_COLOR_VALUE)
    }
}
''',
)

replace_once(
    "modules/customizations/src/com/xaulinxs/customizations/icons/XaulinXsThemedIconColors.kt",
    old='''package com.xaulinxs.customizations.icons

import android.content.Context
import androidx.core.graphics.ColorUtils
import com.android.launcher3.Utilities
import com.android.launcher3.icons.mono.ColorList
import com.android.launcher3.util.WallpaperColorHints

private const val BG_SHADE_RATIO_LIGHT = 0.20f
private const val BG_SHADE_RATIO_DARK = 0.65f
private const val FG_SHADE_RATIO_LIGHT = 0.55f
private const val FG_SHADE_RATIO_DARK = 0.15f

object XaulinXsThemedIconColors {

    fun getColorsIfAvailable(context: Context): ColorList? {
        val primary = WallpaperColorHints.get(context).colors?.primaryColor?.toArgb() ?: return null
        val isDark = Utilities.isDarkTheme(context)

        val background =
            if (isDark) {
                ColorUtils.blendARGB(primary, android.graphics.Color.BLACK, BG_SHADE_RATIO_DARK)
            } else {
                ColorUtils.blendARGB(primary, android.graphics.Color.WHITE, BG_SHADE_RATIO_LIGHT)
            }
        val foreground =
            if (isDark) {
                ColorUtils.blendARGB(primary, android.graphics.Color.WHITE, 1f - FG_SHADE_RATIO_DARK)
            } else {
                ColorUtils.blendARGB(primary, android.graphics.Color.BLACK, FG_SHADE_RATIO_LIGHT)
            }

        return ColorList(
            iconBackgroundColor = background,
            iconForegroundColor = foreground,
            iconAdaptiveBackgroundColor = background,
            badgeBackgroundColor = background,
            badgeForegroundColor = foreground,
        )
    }
}''',
    new='''package com.xaulinxs.customizations.icons

import android.content.Context
import androidx.core.graphics.ColorUtils
import com.android.launcher3.Utilities
import com.android.launcher3.icons.mono.ColorList
import com.android.launcher3.util.WallpaperColorHints
import com.xaulinxs.customizations.theme.XaulinXsManualColor

private const val BG_SHADE_RATIO_LIGHT = 0.20f
private const val BG_SHADE_RATIO_DARK = 0.65f
private const val FG_SHADE_RATIO_LIGHT = 0.55f
private const val FG_SHADE_RATIO_DARK = 0.15f

object XaulinXsThemedIconColors {

    fun getColorsIfAvailable(context: Context): ColorList? {
        val primary = XaulinXsManualColor.getBaseColorIfEnabled(context)
            ?: WallpaperColorHints.get(context).colors?.primaryColor?.toArgb()
            ?: return null
        return buildColorList(primary, Utilities.isDarkTheme(context))
    }

    private fun buildColorList(primary: Int, isDark: Boolean): ColorList {
        val background =
            if (isDark) {
                ColorUtils.blendARGB(primary, android.graphics.Color.BLACK, BG_SHADE_RATIO_DARK)
            } else {
                ColorUtils.blendARGB(primary, android.graphics.Color.WHITE, BG_SHADE_RATIO_LIGHT)
            }
        val foreground =
            if (isDark) {
                ColorUtils.blendARGB(primary, android.graphics.Color.WHITE, 1f - FG_SHADE_RATIO_DARK)
            } else {
                ColorUtils.blendARGB(primary, android.graphics.Color.BLACK, FG_SHADE_RATIO_LIGHT)
            }

        return ColorList(
            iconBackgroundColor = background,
            iconForegroundColor = foreground,
            iconAdaptiveBackgroundColor = background,
            badgeBackgroundColor = background,
            badgeForegroundColor = foreground,
        )
    }
}''',
    label="XaulinXsThemedIconColors.kt usa cor manual",
)

replace_once(
    "modules/customizations/src/com/xaulinxs/customizations/theme/WallpaperScrimHelper.kt",
    old='''import com.android.launcher3.LauncherPrefs
import com.android.launcher3.Utilities
import com.android.launcher3.util.WallpaperColorHints
import com.xaulinxs.customizations.settings.ThemedScrimPreference.Companion.THEMED_SCRIM_ENABLED''',
    new='''import com.android.launcher3.LauncherPrefs
import com.android.launcher3.Utilities
import com.android.launcher3.util.WallpaperColorHints
import com.xaulinxs.customizations.settings.ThemedScrimPreference.Companion.THEMED_SCRIM_ENABLED
import com.xaulinxs.customizations.theme.XaulinXsManualColor''',
    label="import XaulinXsManualColor no WallpaperScrimHelper",
)

replace_once(
    "modules/customizations/src/com/xaulinxs/customizations/theme/WallpaperScrimHelper.kt",
    old='''    fun getScrimColor(context: Context): Int? {
        val primaryColor = WallpaperColorHints.get(context).colors?.primaryColor?.toArgb() ?: return null''',
    new='''    fun getScrimColor(context: Context): Int? {
        // XaulinXs Customizations: cor manual (se ativada) tem prioridade sobre a do wallpaper.
        val primaryColor = XaulinXsManualColor.getBaseColorIfEnabled(context)
            ?: WallpaperColorHints.get(context).colors?.primaryColor?.toArgb()
            ?: return null''',
    label="WallpaperScrimHelper.getScrimColor usa cor manual",
)

write_if_absent(
    "modules/customizations/src/com/xaulinxs/customizations/settings/ManualColorEnabledPreference.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.theme.XaulinXsManualColor

class ManualColorEnabledPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(XaulinXsManualColor.MANUAL_COLOR_ENABLED)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(XaulinXsManualColor.MANUAL_COLOR_ENABLED, newValue as Boolean)
            true
        }
    }
}
''',
)

write_if_absent(
    "modules/customizations/src/com/xaulinxs/customizations/settings/ManualColorPickerPreference.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Editor de cor manual (hex), com preview ao vivo dentro do próprio diálogo.
 * Implementado como Preference comum + AlertDialog no onClick, para não
 * precisar tocar em SettingsActivity.java.
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
import androidx.appcompat.app.AlertDialog
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
            .setTitle(R.string.xaulinxs_manual_color_picker_title)
            .setView(container)
            .setPositiveButton(R.string.xaulinxs_manual_color_save) { _, _ ->
                val parsed = parseHexOrNull(hexInput.text?.toString()) ?: currentColor
                prefs.put(XaulinXsManualColor.MANUAL_COLOR_VALUE, parsed)
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
''',
)

replace_once(
    "res/xml/launcher_preferences.xml",
    old='''        <com.xaulinxs.customizations.settings.WidgetBlurPreference
            android:key="xaulinxs_widget_blur_intensity"
            android:title="@string/xaulinxs_widget_blur_title"
            android:summary="@string/xaulinxs_widget_blur_summary"
            android:persistent="false" />

    </PreferenceScreen>''',
    new='''        <com.xaulinxs.customizations.settings.WidgetBlurPreference
            android:key="xaulinxs_widget_blur_intensity"
            android:title="@string/xaulinxs_widget_blur_title"
            android:summary="@string/xaulinxs_widget_blur_summary"
            android:persistent="false" />

        <com.xaulinxs.customizations.settings.ManualColorEnabledPreference
            android:key="xaulinxs_manual_color_enabled"
            android:title="@string/xaulinxs_manual_color_enabled_title"
            android:summary="@string/xaulinxs_manual_color_enabled_summary"
            android:persistent="false" />

        <com.xaulinxs.customizations.settings.ManualColorPickerPreference
            android:key="xaulinxs_manual_color_picker"
            android:title="@string/xaulinxs_manual_color_picker_title"
            android:persistent="false" />

    </PreferenceScreen>''',
    label="launcher_preferences.xml com os 2 itens de cor manual",
)

replace_once(
    "res/values/xaulinxs_strings.xml",
    old='''    <string name="xaulinxs_widget_blur_summary">Deixa a aparência de cada widget embaçada (0 = nítido)</string>
</resources>''',
    new='''    <string name="xaulinxs_widget_blur_summary">Deixa a aparência de cada widget embaçada (0 = nítido)</string>
    <string name="xaulinxs_manual_color_enabled_title">Usar cor manual</string>
    <string name="xaulinxs_manual_color_enabled_summary">Usa uma cor fixa escolhida por você em vez da cor do papel de parede</string>
    <string name="xaulinxs_manual_color_picker_title">Escolher cor (hex)</string>
    <string name="xaulinxs_manual_color_save">Salvar</string>
</resources>''',
    label="strings da cor manual",
)

print("\nFeature 5 aplicada com sucesso.")
