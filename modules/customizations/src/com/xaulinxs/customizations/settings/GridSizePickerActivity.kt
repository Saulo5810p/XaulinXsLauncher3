/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Feature nova (info.txt/etapa 3): trocar o número de colunas/linhas da
 * tela inicial, de 2x2 até 10x10. As grades em si são definidas como
 * <grid-option> normais em res/xml/device_profiles.xml (mesmo mecanismo
 * que o AOSP já usa pras grades originais/padrão) — esta Activity só
 * lista as que a gente adicionou (prefixo "xaulinxs_") e aplica a
 * escolhida via InvariantDeviceProfile.setCurrentGrid(), que já existe
 * pronto no AOSP e cuida de tudo (troca de banco de dados, notifica
 * quem estiver ouvindo mudança de IDP, etc.).
 *
 * Lista construída dinamicamente a partir de parseAllGridOptions() em vez
 * de hardcoded, pra nunca ficar dessincronizada do XML.
 *
 * android.app.Activity puro (não AppCompat) — mesmo motivo documentado em
 * ManualColorPickerPreference.
 */
package com.xaulinxs.customizations.settings

import android.app.Activity
import android.os.Bundle
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.android.launcher3.LauncherAppState
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.R

private const val GRID_OPTION_PREFIX = "xaulinxs_"

class GridSizePickerActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val density = resources.displayMetrics.density
        val paddingPx = (24 * density).toInt()

        val idp = LauncherAppState.getIDP(this)
        val currentGridName = LauncherPrefs.get(this).get(LauncherPrefs.GRID_NAME)

        val options = idp.parseAllGridOptions(this)
            .filter { it.name.startsWith(GRID_OPTION_PREFIX) }
            .sortedBy { it.numRows * it.numColumns }

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(paddingPx, paddingPx, paddingPx, paddingPx)
        }

        container.addView(TextView(this).apply {
            text = getString(R.string.xaulinxs_grid_size_title)
            textSize = 20f
            setPadding(0, 0, 0, paddingPx / 2)
        })

        if (options.isEmpty()) {
            container.addView(TextView(this).apply {
                text = "Nenhuma grade customizada encontrada em device_profiles.xml"
            })
        }

        options.forEach { option ->
            val label = "${option.numColumns}x${option.numRows}"
            container.addView(Button(this).apply {
                text = if (option.name == currentGridName) "$label ✓" else label
                gravity = Gravity.CENTER
                setOnClickListener {
                    idp.setCurrentGrid(option.name)
                    finish()
                }
            })
        }

        val scroll = ScrollView(this).apply { addView(container) }
        setContentView(scroll)
        title = getString(R.string.xaulinxs_grid_size_title)
    }
}
