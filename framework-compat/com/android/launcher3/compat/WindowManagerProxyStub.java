package com.android.launcher3.compat;

import android.content.Context;
import android.graphics.Rect;

/**
 * Stub de compatibilidade para WindowManagerProxy do AOSP 17.
 * Fornece métricas de tela em fallback para dispositivos sem privilégios AOSP.
 */
public class WindowManagerProxyStub {
    private static WindowManagerProxyStub sInstance;

    public static WindowManagerProxyStub getInstance(Context context) {
        if (sInstance == null) {
            sInstance = new WindowManagerProxyStub();
        }
        return sInstance;
    }

    public Rect getDisplayBounds(Context context) {
        return new Rect(0, 0, 1080, 2400);
    }

    public int getRotation(Context context) {
        return 0;
    }
}
