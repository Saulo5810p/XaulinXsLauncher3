package com.android.launcher3.compat;

import android.content.Context;

/**
 * Stub de compatibilidade para SystemUiProxy do AOSP 17.
 * Fornece implementações no-op para permitir compilação sem depender do SystemUI do SO.
 */
public class SystemUiProxyStub {
    private static SystemUiProxyStub sInstance;

    public static SystemUiProxyStub INSTANCE = new SystemUiProxyStub();

    public static SystemUiProxyStub getInstance(Context context) {
        if (sInstance == null) {
            sInstance = new SystemUiProxyStub();
        }
        return sInstance;
    }

    public void setBackButtonAlpha(float alpha, boolean animate) {}
    public void setNavBarMode(int mode) {}
    public void onOverviewShown(boolean fromHome) {}
    public void stopScreenPinning() {}
    public void onBackPressed() {}
}
