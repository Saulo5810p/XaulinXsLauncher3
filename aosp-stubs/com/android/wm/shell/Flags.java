package com.android.wm.shell;

/**
 * Stub manual para com.android.wm.shell.Flags (aconfig do WindowManager Shell).
 * Mesmo nome de alguns métodos de com.android.launcher3.Flags — são namespaces
 * de aconfig diferentes, o AOSP realmente duplica flags entre módulos.
 */
public final class Flags {
    private Flags() {}

    public static boolean enableTinyTaskbar() { return false; }
    public static boolean enableBubbleBar() { return false; }
    public static boolean enableBubbleBarOnPhones() { return false; }
    public static boolean enable2x1Split() { return false; }
    public static boolean enableGsf() { return false; }
}
