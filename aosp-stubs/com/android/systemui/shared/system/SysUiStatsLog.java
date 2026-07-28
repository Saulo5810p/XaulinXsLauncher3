package com.android.systemui.shared.system;

/**
 * Stub manual para SysUiStatsLog (normalmente gerado por statsd/proto no AOSP).
 * Os valores numéricos não importam pro launcher funcionar — só afetam
 * telemetria interna do sistema, que não existe fora da árvore do AOSP.
 */
public final class SysUiStatsLog {
    private SysUiStatsLog() {}

    public static final int LAUNCHER_UICHANGED__USER_TYPE__TYPE_UNKNOWN = 0;
    public static final int LAUNCHER_UICHANGED__USER_TYPE__TYPE_MAIN = 1;
    public static final int LAUNCHER_UICHANGED__USER_TYPE__TYPE_WORK = 2;
    public static final int LAUNCHER_UICHANGED__USER_TYPE__TYPE_CLONED = 3;
    public static final int LAUNCHER_UICHANGED__USER_TYPE__TYPE_PRIVATE = 4;
}
