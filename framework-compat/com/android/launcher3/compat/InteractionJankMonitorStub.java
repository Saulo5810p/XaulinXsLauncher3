package com.android.launcher3.compat;

import android.view.View;

/**
 * Stub para o InteractionJankMonitor (API Oculta do SystemUI do AOSP 17).
 * Evita exceções ao rastrear métricas de animações de transição.
 */
public class InteractionJankMonitorStub {
    private static InteractionJankMonitorStub sInstance;

    public static InteractionJankMonitorStub getInstance() {
        if (sInstance == null) {
            sInstance = new InteractionJankMonitorStub();
        }
        return sInstance;
    }

    public boolean begin(View v, int cujType) {
        return true;
    }

    public boolean end(int cujType) {
        return true;
    }

    public boolean cancel(int cujType) {
        return true;
    }
}
