package com.android.systemui.plugins;

import android.content.Context;

/** Stub manual — métodos default no-op, já que o PluginManagerWrapper nunca os chama de verdade. */
public interface PluginListener<T extends Plugin> {
    default void onPluginConnected(T plugin, Context context) {}
    default void onPluginDisconnected(T plugin) {}
    default void onPluginLoaded(T plugin, Context pluginContext,
            PluginLifecycleManager<T> manager) {}
    default void onPluginUnloaded(T plugin, PluginLifecycleManager<T> manager) {}
}
