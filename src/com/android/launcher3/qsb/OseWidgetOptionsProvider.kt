/*
 * Copyright (C) 2025 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.android.launcher3.qsb

import android.appwidget.AppWidgetProviderInfo.WIDGET_FEATURE_RECONFIGURABLE
import android.content.Intent
import android.util.Log
import com.android.launcher3.BaseActivity
import com.android.launcher3.R
import com.android.launcher3.logging.StatsLogManager
import com.android.launcher3.popup.PopupCategory
import com.android.launcher3.popup.PopupData
import com.android.launcher3.views.ActivityContext
import com.xaulinxs.customizations.qsb.QsbConfigActivity
import javax.inject.Inject

/** Provides option items when QSB is long pressed. */
open class OseWidgetOptionsProvider
@Inject
constructor(
    private val oseWidgetManager: OseWidgetManager,
    private val activityContext: ActivityContext,
) {

    // XaulinXs Customizations: a QSB nunca mais binda um AppWidget de
    // terceiro (ver OseWidgetManager.handleOseInfoUpdate), então
    // appWidgetSupportsReconfigure() abaixo é sempre false e a lista de
    // opções do AOSP original ficava permanentemente vazia — o
    // long-press não abria mais nada. Fix: sempre oferecer um item de
    // "Configurar barra de busca" apontando pra QsbConfigActivity
    // (tela própria do launcher, não mais configuração de widget de
    // terceiro), reproduzindo o mesmo balão que o widget do Google
    // mostrava antes.
    open fun getOptionItems(): List<PopupData> {
        val qsbSettingsItem =
            PopupData(
                iconResId = R.drawable.ic_setting,
                labelResId = R.string.xaulinxs_qsb_config_menu_item,
                category = PopupCategory.SYSTEM_SHORTCUT_FIXED,
                eventId = StatsLogManager.LauncherEvent.LAUNCHER_QSB_WIDGET_SETTINGS_TAP,
            ) { activityContext, _, _ ->
                // Mesmo padrão do código original (que castava pra
                // BaseActivity antes de chamar oseWidgetManager.startConfigActivity):
                // o tipo do parâmetro do lambda vem da API compilada de
                // PopupData, então o cast explícito garante acesso a
                // startActivity() independente do tipo estático exposto.
                val activity = activityContext as BaseActivity
                activity.startActivity(Intent(activity, QsbConfigActivity::class.java))
            }
        return listOf(qsbSettingsItem)
    }

    /**
     * Checks whether the widget supports configuration.
     *
     * A widget supports configuration if it has a configuration activity
     *
     * @return true if the widget supports configuration, false otherwise.
     */
    fun appWidgetSupportsReconfigure(): Boolean {
        val providerInfo = oseWidgetManager.providerInfo.value
        val featureFlags = providerInfo?.widgetFeatures ?: 0
        val canReconfigure = (featureFlags and WIDGET_FEATURE_RECONFIGURABLE) != 0
        if (DEBUG) {
            Log.i(
                TAG,
                "configurationActivity = " +
                    providerInfo?.configure +
                    " reconfigurable= " +
                    (featureFlags and WIDGET_FEATURE_RECONFIGURABLE),
            )
        }
        return providerInfo?.configure != null && canReconfigure
    }

    companion object {
        private const val TAG = "SearchWidgetOptionsProvider"
        private const val DEBUG = false
    }
}
