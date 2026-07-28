package com.android.launcher3.compat;

import android.app.ActivityManager;
import android.content.Context;

/**
 * Stub de compatibilidade para ActivityManagerWrapper do AOSP.
 * Redireciona chamadas ocultas de ActivityManager para métodos da API pública do Android.
 */
public class ActivityManagerWrapperStub {
    private static ActivityManagerWrapperStub sInstance;

    public static ActivityManagerWrapperStub getInstance() {
        if (sInstance == null) {
            sInstance = new ActivityManagerWrapperStub();
        }
        return sInstance;
    }

    public boolean isScreenPinningActive(Context context) {
        ActivityManager am = (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
        if (am == null) return false;
        return am.getLockTaskModeState() != ActivityManager.LOCK_TASK_MODE_NONE;
    }

    public void closeSystemWindows(Context context) {
        // Operação no-op em launchers sem permissões de sistema
    }
}
