/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Aplica o wallpaper de marca do XaulinXs Launcher na primeira execução do
 * app. Ação de uma vez só (item persistido via LauncherPrefs). Depois disso
 * o usuário pode trocar de wallpaper livremente, sem interferência nossa.
 */
package com.xaulinxs.customizations.theme

import android.app.WallpaperManager
import android.content.Context
import android.graphics.BitmapFactory
import android.util.Log
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem
import com.android.launcher3.util.Executors

private const val TAG = "DefaultWallpaperApplier"
private const val ASSET_NAME = "identidade_wallpaper.png"

object DefaultWallpaperApplier {

    private val DEFAULT_WALLPAPER_APPLIED = backedUpItem("xaulinxs_default_wallpaper_applied", false)

    @JvmStatic
    fun applyOnFirstRunIfNeeded(context: Context) {
        val prefs = LauncherPrefs.get(context)
        if (prefs.get(DEFAULT_WALLPAPER_APPLIED)) return

        Executors.THREAD_POOL_EXECUTOR.execute {
            try {
                val options = BitmapFactory.Options().apply { inSampleSize = 2 }
                val bitmap = context.assets.open(ASSET_NAME).use { input ->
                    BitmapFactory.decodeStream(input, null, options)
                }
                if (bitmap != null) {
                    WallpaperManager.getInstance(context).setBitmap(bitmap)
                    prefs.put(DEFAULT_WALLPAPER_APPLIED, true)
                    Log.d(TAG, "Wallpaper padrão XaulinXs aplicado com sucesso")
                } else {
                    Log.w(TAG, "Falha ao decodificar $ASSET_NAME")
                }
            } catch (e: Exception) {
                Log.w(TAG, "Não foi possível aplicar o wallpaper padrão", e)
            }
        }
    }
}
