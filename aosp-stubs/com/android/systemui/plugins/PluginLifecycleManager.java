package com.android.systemui.plugins;

import android.content.ComponentName;

/** Stub manual — superfície mínima usada pelo Launcher3 (CustomWidgetManager). */
public interface PluginLifecycleManager<T extends Plugin> {
    ComponentName getComponentName();
}
