package com.android.launcher3.compat;

import android.os.Build;
import android.view.View;
import android.view.Window;

/**
 * Ponte de compatibilidade para efeitos de desfoque (Blur) no Launcher.
 * Garante blur nativo em Android 12+ (API 31+) e fallback visual elegante em versões anteriores.
 */
public class BlurBridge {

    public static boolean isBlurSupported() {
        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.S;
    }

    public static void applyWindowBlur(Window window, int blurRadius) {
        if (isBlurSupported() && window != null) {
            try {
                window.setBackgroundBlurRadius(blurRadius);
            } catch (Throwable ignored) {
                // Fallback silencioso para dispositivos sem suporte de driver GPU
            }
        }
    }

    public static void applyViewFallbackBackground(View view, int fallbackColor) {
        if (!isBlurSupported() && view != null) {
            view.setBackgroundColor(fallbackColor);
        }
    }
}
