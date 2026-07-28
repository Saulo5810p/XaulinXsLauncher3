package com.android.launcher3.compat;

import android.content.Context;

/**
 * Stub de compatibilidade para o RecentsModel.
 * Desativa a integração obrigatória de recentes quando rodando como launcher standalone.
 */
public class RecentsModelStub {
    private static RecentsModelStub sInstance;

    public static RecentsModelStub getInstance(Context context) {
        if (sInstance == null) {
            sInstance = new RecentsModelStub();
        }
        return sInstance;
    }

    public void registerTaskStackListener() {}
    public void unregisterTaskStackListener() {}
    public boolean isRecentsEnabled() {
        return false;
    }
}
