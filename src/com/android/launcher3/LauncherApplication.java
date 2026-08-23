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
import android.content.Context;
import com.android.launcher3.dagger.DaggerLauncherAppComponent;
import com.android.launcher3.dagger.LauncherAppComponent;
import com.android.launcher3.dagger.LauncherBaseAppComponent;
import com.android.launcher3.dagger.LauncherComponentProvider;
import com.android.launcher3.util.TraceHelper;
import com.xaulinxs.customizations.theme.XaulinXsThemeColorResources;
import com.xaulinxs.customizations.theme.XaulinXsThemedContextWrapper;

public class LauncherApplication extends Application {

    private volatile LauncherBaseAppComponent mAppComponent;

    // XaulinXs Customizations — "UI-UX Custom Colors": envolve o Context
    // base do processo com um wrapper que intercepta @color/materialColorX
    // (ver XaulinXsThemeColorResources.kt para o porquê disso, em vez de
    // tentar reescrever o XML empacotado no APK). Precisa ser attachBaseContext,
    // não onCreate: getResources() já é chamado antes de onCreate rodar.
    @Override
    protected void attachBaseContext(Context base) {
        super.attachBaseContext(new XaulinXsThemedContextWrapper(base));
    }

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
