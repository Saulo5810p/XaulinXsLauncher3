/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Interruptor pedido pelo usuário: liga/desliga o wallpaper PRÓPRIO do
 * R's Home3 (XaulinXsInAppWallpaper). Ligado (padrão) = comportamento
 * atual, nosso wallpaper desenhado por baixo do Workspace. Desligado =
 * XaulinXsWallpaperView não desenha nada, deixando o wallpaper real do
 * sistema aparecer por trás (ela já é o 1º filho do DragLayer, atrás de
 * tudo, então não precisa esconder a View — só parar de pintar).
 */
package com.xaulinxs.customizations.theme

import com.android.launcher3.LauncherPrefs.Companion.backedUpItem
import com.android.launcher3.util.Executors
import java.util.concurrent.CopyOnWriteArrayList

object XaulinXsInAppWallpaperSetting {

    @JvmField
    val IN_APP_WALLPAPER_ENABLED = backedUpItem("xaulinxs_in_app_wallpaper_enabled", true)

    private val listeners = CopyOnWriteArrayList<() -> Unit>()

    @JvmStatic
    fun addOnChangedListener(listener: () -> Unit) {
        listeners.add(listener)
    }

    @JvmStatic
    fun removeOnChangedListener(listener: () -> Unit) {
        listeners.remove(listener)
    }

    @JvmStatic
    fun notifyChanged() {
        Executors.MAIN_EXECUTOR.execute { listeners.forEach { it() } }
    }
}
