/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherAppState
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.icons.XaulinXsIconLabels.LABELS_HIDDEN

class IconLabelsPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(LABELS_HIDDEN)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(LABELS_HIDDEN, newValue as Boolean)
            // XaulinXs Customizations: força o rebind de todos os ícones (home,
            // hotseat, pastas, app drawer) pra aplicar/remover os labels na hora.
            LauncherAppState.getInstance(context).model.forceReload("xaulinxs_icon_labels_toggle")
            true
        }
    }
}
