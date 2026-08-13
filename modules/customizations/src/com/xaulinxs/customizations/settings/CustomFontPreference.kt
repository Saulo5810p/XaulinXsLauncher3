/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Diálogo com duas ações: "Importar fonte" (abre o file manager próprio
 * via startActivityForResult) e "Restaurar padrão" (limpa a fonte
 * customizada). O resultado da importação chega via
 * LauncherSettingsFragment.onActivityResult (ver SettingsActivity.java),
 * que repassa para handleActivityResult() abaixo.
 */
package com.xaulinxs.customizations.settings

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.util.AttributeSet
import android.widget.Toast
import android.app.AlertDialog
import androidx.preference.Preference
import androidx.preference.PreferenceFragmentCompat
import com.android.launcher3.R
import com.xaulinxs.customizations.font.XaulinXsCustomFont
import com.xaulinxs.customizations.font.XaulinXsFontFileManagerActivity
import java.io.File

class CustomFontPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : Preference(context, attrs) {

    init {
        isPersistent = false
        updateSummary()
    }

    override fun onClick() {
        AlertDialog.Builder(context)
            .setTitle(R.string.xaulinxs_custom_font_title)
            .setMessage(currentFontLabel())
            .setPositiveButton(R.string.xaulinxs_font_choose) { _, _ -> launchFontPicker() }
            .setNeutralButton(R.string.xaulinxs_font_reset) { _, _ ->
                XaulinXsCustomFont.setCustomFontPath(context, null)
                updateSummary()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun launchFontPicker() {
        val intent = Intent(context, XaulinXsFontFileManagerActivity::class.java)
        try {
            (context as? Activity)?.startActivityForResult(intent, REQUEST_CODE_PICK_FONT)
        } catch (e: Exception) {
            Toast.makeText(context, R.string.xaulinxs_filemanager_import_error, Toast.LENGTH_SHORT).show()
        }
    }

    fun onFontImported(path: String) {
        XaulinXsCustomFont.setCustomFontPath(context, path)
        updateSummary()
    }

    private fun currentFontLabel(): String {
        val path = XaulinXsCustomFont.getCustomFontPath(context)
        return if (path == null) {
            context.getString(R.string.xaulinxs_font_none)
        } else {
            context.getString(R.string.xaulinxs_font_current, File(path).name)
        }
    }

    private fun updateSummary() {
        summary = currentFontLabel()
    }

    companion object {
        const val REQUEST_CODE_PICK_FONT = 7001
        private const val PREF_KEY = "xaulinxs_custom_font"

        @JvmStatic
        fun handleActivityResult(
            fragment: PreferenceFragmentCompat,
            requestCode: Int,
            resultCode: Int,
            data: Intent?,
        ) {
            if (requestCode != REQUEST_CODE_PICK_FONT || resultCode != Activity.RESULT_OK || data == null) return
            val path = data.getStringExtra(XaulinXsFontFileManagerActivity.EXTRA_SELECTED_FONT_PATH) ?: return
            (fragment.findPreference(PREF_KEY) as? CustomFontPreference)?.onFontImported(path)
        }
    }
}
