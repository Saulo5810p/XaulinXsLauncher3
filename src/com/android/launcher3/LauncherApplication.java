/*
 * Copyright (C) 2023 The Android Open Source Project
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
package com.android.launcher3;

import android.app.Application;
import com.android.launcher3.dagger.DaggerLauncherAppComponent;
import com.android.launcher3.dagger.LauncherAppComponent;
import com.android.launcher3.dagger.LauncherBaseAppComponent;
import com.android.launcher3.dagger.LauncherComponentProvider;
import com.android.launcher3.util.TraceHelper;
import com.xaulinxs.customizations.theme.XaulinXsThemeColorResources;

public class LauncherApplication extends Application {

    private volatile LauncherBaseAppComponent mAppComponent;

    // XaulinXs Customizations — "UI-UX Custom Colors": NÃO envolver o
    // Context da Application inteira aqui (attachBaseContext). Isso já
    // foi tentado e causou crash real em produção: o framework Android
    // faz cast interno de Context para ContextImpl em vários pontos que
    // não passam pela Activity — por exemplo BroadcastReceiver
    // (ActivityThread.handleReceiver) — e um ContextWrapper substituindo
    // o Context "base" do processo inteiro quebra esse cast
    // (ClassCastException: XaulinXsThemedContextWrapper cannot be cast
    // to ContextImpl), derrubando SessionCommitReceiver e qualquer outro
    // receiver/service que dependa do Context puro da Application. A
    // interceptação de cor fica só nas Activities (Launcher,
    // SettingsActivity, CustomColorsActivity), que é onde a UI é
    // realmente inflada — ver XaulinXsThemeColorResources.kt.
    @Override
    public void onCreate() {
        super.onCreate();
        XaulinXsThemeColorResources.installIfEnabled(this);
        LauncherComponentProvider.get(this).getMainProcessInitializer().init(this);
    }

    public LauncherAppComponent getAppComponent() {
        if (mAppComponent == null) {
            synchronized (this) {
                if (mAppComponent == null) {
                    initDaggerComponent(DaggerLauncherAppComponent.builder()
                            .iconsDbName(LauncherFiles.APP_ICONS_DB));
                }
            }
        }
        return (LauncherAppComponent) mAppComponent;
    }

    public void initDaggerComponent(LauncherBaseAppComponent.Builder componentBuilder) {
        mAppComponent = componentBuilder
                .appContext(this)
                .setSafeModeEnabled(TraceHelper.allowIpcs(
                        "isSafeMode", () -> getPackageManager().isSafeMode()))
                .build();
    }
}
