package com.android.launcher3.compat;

import android.content.Context;

/**
 * Stub para o TaskbarManager.
 * Em um launcher de usuário (sem permissões de sistema), a taskbar do AOSP não é ancorada no SystemUI.
 */
public class TaskbarManagerStub {
    private static TaskbarManagerStub sInstance;

    public static TaskbarManagerStub getInstance(Context context) {
        if (sInstance == null) {
            sInstance = new TaskbarManagerStub();
        }
        return sInstance;
    }

    public void recreateTaskbar() {}
    public void destroyTaskbar() {}
    public boolean isTaskbarPresent() {
        return false;
    }
}
