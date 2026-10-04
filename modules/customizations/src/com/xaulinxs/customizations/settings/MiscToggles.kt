/*
 * XaulinXs R's Misc — não faz parte do AOSP original.
 *
 * Interruptores da categoria "R's Misc".
 */
package com.xaulinxs.customizations.settings

import android.app.Activity
import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.XaulinXsAppRestarter
import com.xaulinxs.customizations.misc.XaulinXsMiscPermissionActivity
import com.xaulinxs.customizations.misc.XaulinXsMiscPermissions
import com.xaulinxs.customizations.misc.XaulinXsMiscSettings

/** Liga/desliga a página fixa de música. A página nasce no bind do Workspace, então reinicia o app. */
class MusicPageEnabledPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = XaulinXsMiscSettings.isMusicPageEnabled(context)
        setOnPreferenceChangeListener { _, newValue ->
            val enabled = newValue as Boolean
            LauncherPrefs.get(context).put(XaulinXsMiscSettings.MUSIC_PAGE_ENABLED, enabled)
            if (enabled) {
                XaulinXsMiscPermissionActivity.request(context, XaulinXsMiscPermissions.AUDIO)
            }
            (context as? Activity)?.let { XaulinXsAppRestarter.restart(it) }
            true
        }
    }
}

/** Liga/desliga o clima; ao ativar, mostra o popup de localização. */
class WeatherEnabledPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = XaulinXsMiscSettings.isWeatherEnabled(context)
        setOnPreferenceChangeListener { _, newValue ->
            val enabled = newValue as Boolean
            LauncherPrefs.get(context).put(XaulinXsMiscSettings.WEATHER_ENABLED, enabled)
            if (enabled) {
                XaulinXsMiscPermissionActivity.request(context, XaulinXsMiscPermissions.LOCATION)
            }
            // O Launcher relê o interruptor no onResume ao voltar para a tela inicial.
            true
        }
    }
}
