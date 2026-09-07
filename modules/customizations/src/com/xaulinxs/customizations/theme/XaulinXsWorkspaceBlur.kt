/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Feature nova (info.txt/etapa 3: "Área de trabalho [...] - desfoque").
 * Desfoque desligado por padrão (raio 0 = sem nenhuma mudança visual).
 */
package com.xaulinxs.customizations.theme

import android.content.Context
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem
import java.util.concurrent.CopyOnWriteArrayList

private const val KEY_WORKSPACE_BLUR_PERCENT = "xaulinxs_workspace_blur_percent"
private const val MAX_BLUR_RADIUS_DP = 25f

object XaulinXsWorkspaceBlur {

    const val MIN_PERCENT = 0
    const val MAX_PERCENT = 100

    val WORKSPACE_BLUR_PERCENT = backedUpItem(KEY_WORKSPACE_BLUR_PERCENT, MIN_PERCENT)

    private val listeners = CopyOnWriteArrayList<() -> Unit>()

    @JvmStatic
    fun getBlurRadiusPx(context: Context): Float {
        val percent = LauncherPrefs.get(context).get(WORKSPACE_BLUR_PERCENT)
            .coerceIn(MIN_PERCENT, MAX_PERCENT)
        if (percent <= 0) return 0f
        val density = context.resources.displayMetrics.density
        return (MAX_BLUR_RADIUS_DP * percent / 100f) * density
    }

    /** Chamar sempre que WORKSPACE_BLUR_PERCENT for alterado (ver preference). */
    @JvmStatic
    fun notifyChanged() {
        listeners.forEach { it() }
    }

    @JvmStatic
    fun addOnChangedListener(listener: () -> Unit) {
        listeners.add(listener)
    }

    @JvmStatic
    fun removeOnChangedListener(listener: () -> Unit) {
        listeners.remove(listener)
    }
}
