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

import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetManager.INVALID_APPWIDGET_ID
import android.appwidget.AppWidgetProviderInfo
import android.appwidget.AppWidgetProviderInfo.WIDGET_CATEGORY_SEARCHBOX
import android.appwidget.AppWidgetProviderInfo.WIDGET_FEATURE_CONFIGURATION_OPTIONAL
import android.appwidget.AppWidgetProviderInfo.WIDGET_FEATURE_HIDE_FROM_PICKER
import android.content.ActivityNotFoundException
import android.content.Context
import android.os.Process.myUserHandle
import android.util.Log
import android.widget.Toast
import androidx.annotation.VisibleForTesting
import com.android.launcher3.BaseActivity
import com.android.launcher3.InvariantDeviceProfile
import com.android.launcher3.InvariantDeviceProfile.OnIDPChangeListener
import com.android.launcher3.LauncherConstants.ActivityCodes.REQUEST_RECONFIGURE_APPWIDGET
import com.android.launcher3.R
import com.android.launcher3.dagger.ApplicationContext
import com.android.launcher3.dagger.LauncherAppSingleton
import com.android.launcher3.graphics.theme.ThemePreference
import com.android.launcher3.qsb.OSEManager.Companion.OSE_LOOPER
import com.android.launcher3.qsb.OSEManager.OSEInfo
import com.android.launcher3.util.DaggerSingletonTracker
import com.android.launcher3.util.PackageUserKey
import com.android.launcher3.widget.WidgetManagerHelper
import com.android.launcher3.widget.util.WidgetSizeHandler
import javax.inject.Inject

/**
 * Manager for default search widget
 *
 * Listens to OSEManager for any OSE changes and provides the updated widget configurations
 */
@LauncherAppSingleton
class OseWidgetManager
@Inject
constructor(
    @ApplicationContext private val context: Context,
    oseManager: OSEManager,
    private val widgetHost: QsbAppWidgetHost,
    private val sizeHandler: WidgetSizeHandler,
    private val idp: InvariantDeviceProfile,
    tracker: DaggerSingletonTracker,
    themePreference: ThemePreference,
) {

    private val mutableState = QsbAppWidgetHost.MutableState()

    val providerInfo = mutableState.providerInfo.asListenable()
    val views = mutableState.views.asListenable()

    private val executor = OSE_LOOPER

    init {
        tracker.addCloseable(widgetHost.addCallbacks(mutableState))
        tracker.addCloseable(oseManager.oseInfo.forEach(executor, this::handleOseInfoUpdate))

        val idpListener = OnIDPChangeListener { updateWidgetSizeAsync() }
        idp.addOnChangeListener(idpListener)
        tracker.addCloseable(themePreference.forEach(executor) { updateWidgetSizeAsync() })
        tracker.addCloseable { idp.removeOnChangeListener(idpListener) }
    }

    private fun handleOseInfoUpdate(@Suppress("UNUSED_PARAMETER") info: OSEInfo) {
        // XaulinXs Customizations: esta é a QSB nativa AOSP/Launcher3
        // "NoQuickstep", não o Pixel Launcher com Widget de busca do
        // Google. O comportamento AOSP original bindava um AppWidget
        // real (RemoteViews de terceiro) do "on-device search engine"
        // configurado no sistema — no caso comum (Google como app
        // padrão), isso injetava o widget real de busca do Google na
        // QSB, e por consequência: (1) o long-press na QSB abria as
        // configurações desse widget de terceiro via
        // OseWidgetOptionsProvider/startConfigActivity, e (2) a QSB
        // ficava sujeita ao mesmo problema de RemoteViews.apply()
        // reutilizando o LayoutInflater da Activity que afeta qualquer
        // AppWidgetHostView (ver XaulinXsGlobalFontInflaterFactory).
        // Fix: nunca localiza/binda um AppWidget de terceiro — sempre
        // despacha valores nulos, o que faz o framework
        // (AppWidgetHostView.updateAppWidget(null)) cair automaticamente
        // em OseWidgetView.getErrorView(), a própria UI estática nativa
        // do AOSP (ícone + label + clique abre busca/browser), sem
        // nenhuma RemoteViews de terceiro envolvida e sem opção de
        // configuração no long-press. widgetHost.getBoundWidgetId()
        // permanece disponível para limpar qualquer widget já bindado
        // de uma sessão anterior (antes deste fix).
        val currentWidgetId = widgetHost.getBoundWidgetId()
        if (currentWidgetId != INVALID_APPWIDGET_ID) {
            widgetHost.deleteAppWidgetId(currentWidgetId)
        }
        widgetHost.setActiveWidget(INVALID_APPWIDGET_ID, null)
        dispatchNullValues()
    }

    private fun updateWidgetSizeAsync() {
        val widgetId = widgetHost.getActiveWidgetId()
        if (widgetId != INVALID_APPWIDGET_ID) {
            sizeHandler.updateHotseatQsbSizeRangesAsync(widgetId, executor)
        }
    }

    private fun dispatchNullValues() {
        if (mutableState.providerInfo.value != null) mutableState.providerInfo.dispatchValue(null)
        if (mutableState.views.value != null) mutableState.views.dispatchValue(null)
    }

    fun startConfigActivity(activity: BaseActivity): Boolean {
        val widgetId = widgetHost.getActiveWidgetId()
        if (widgetId == 0) {
            Log.e(TAG, "Couldn't find a valid widgetId")
            return false
        }
        try {
            widgetHost.startAppWidgetConfigureActivityForResult(
                activity,
                widgetId,
                0,
                REQUEST_RECONFIGURE_APPWIDGET,
                activity
                    .makeDefaultActivityOptions(-1 /* SPLASH_SCREEN_STYLE_UNDEFINED */)
                    .toBundle(),
            )
            return true
        } catch (e: ActivityNotFoundException) {
            Toast.makeText(activity, R.string.activity_not_found, Toast.LENGTH_SHORT).show()
        } catch (e: SecurityException) {
            Log.e(TAG, "Security Exception " + e)
        }
        return false
    }

    companion object {
        private const val TAG = "OseWidgetManager"

        @VisibleForTesting
        fun findSearchWidgetForPackage(context: Context, pkg: String): AppWidgetProviderInfo? {
            val allEligibleWidgets =
                WidgetManagerHelper(context)
                    .getAllProviders(PackageUserKey(pkg, myUserHandle()))
                    .filter {
                        it.configure == null ||
                            ((it.widgetFeatures and WIDGET_FEATURE_CONFIGURATION_OPTIONAL) != 0)
                    }
            val allSearchBoxWidgets =
                allEligibleWidgets.filter { (it.widgetCategory and WIDGET_CATEGORY_SEARCHBOX) != 0 }
            return allSearchBoxWidgets.firstOrNull {
                // If multiple search box widgets are available, choose the widget that is
                // not hidden from the picker
                (it.widgetFeatures and WIDGET_FEATURE_HIDE_FROM_PICKER) == 0
            } ?: allSearchBoxWidgets.firstOrNull() ?: allEligibleWidgets.firstOrNull()
        }
    }
}
