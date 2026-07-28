package com.android.systemui.plugins;

/**
 * Stub manual da interface marcadora Plugin (vem de PluginCoreLib no AOSP,
 * que não existe fora da árvore do sistema). Como o PluginManagerWrapper do
 * Launcher3 já é no-op (nunca conecta plugins de verdade), só precisamos que
 * isso compile — não precisa de comportamento real.
 */
public interface Plugin {
    default String getTag() { return getClass().getSimpleName(); }
}
