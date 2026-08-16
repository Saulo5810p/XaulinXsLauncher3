/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Diálogo com duas ações: "Importar fonte" (abre o file manager próprio
 * via startActivityForResult) e "Restaurar padrão" (limpa a fonte
 * customizada). O resultado da importação chega via
 * LauncherSettingsFragment.onActivityResult (ver SettingsActivity.java),
 * que repassa para handleActivityResult() abaixo.
 *
 * XaulinXs fix (causa raiz real do "fonte não muda ao importar" —
 * substitui a tentativa anterior via reapplyToVisibleIcons, que tratava
 * um sintoma e não a causa): o startActivityForResult original era
 * chamado na Activity (via cast de context), não no Fragment. Quando o
 * request é aberto assim, o FragmentManager não associa aquele
 * requestCode ao fragment que originou a ação — o resultado volta para
 * SettingsActivity.onActivityResult (a Activity), que nunca está
 * sobrescrito e não repassa manualmente para o fragment. Consequência:
 * LauncherSettingsFragment.onActivityResult NUNCA era chamado,
 * handleActivityResult() nunca rodava, setCustomFontPath() nunca era
 * chamado — a fonte escolhida nunca era de fato salva, então não havia
 * nada para reaplicar no onResume do Launcher (esse mecanismo estava
 * correto, só nunca tinha um path novo para aplicar). Fix: guardar a
 * referência ao PreferenceFragmentCompat dono, entregue explicitamente
 * por LauncherSettingsFragment.onCreatePreferences() logo após inflar a
 * tela (ver setOwnerFragment() e SettingsActivity.java), e chamar
 * fragment.startActivityForResult(), que É registrado corretamente pelo
 * FragmentManager e entrega o resultado no onActivityResult do fragment.
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
import java.lang.ref.WeakReference

class CustomFontPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : Preference(context, attrs) {

    private var fragmentRef: WeakReference<PreferenceFragmentCompat>? = null

    init {
        isPersistent = false
        updateSummary()
    }

    /**
     * Chamado por LauncherSettingsFragment.onCreatePreferences() logo após
     * a preference ser encontrada na tela inflada — é o ponto em que
     * temos acesso ao PreferenceFragmentCompat real que hospeda esta
     * preference (o construtor só recebe o Context, que aqui é a
     * Activity, não o fragment).
     */
    fun setOwnerFragment(fragment: PreferenceFragmentCompat) {
        fragmentRef = WeakReference(fragment)
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
        val fragment = fragmentRef?.get()
        try {
            if (fragment != null) {
                // Caminho correto: o FragmentManager registra este
                // requestCode contra o fragment e entrega o resultado no
                // onActivityResult dele.
                fragment.startActivityForResult(intent, REQUEST_CODE_PICK_FONT)
            } else {
                Toast.makeText(context, R.string.xaulinxs_filemanager_import_error, Toast.LENGTH_SHORT).show()
            }
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
