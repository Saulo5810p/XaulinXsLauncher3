/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 * XAULINXS_BLUR_V3
 *
 * Cópia (snapshot) do wallpaper ATUAL DO SISTEMA, usada só para poder desfocá-lo
 * quando o wallpaper próprio do launcher está desligado.
 *
 * Por quê: o wallpaper do sistema não é desenhado pela janela do Launcher (é a
 * janela de wallpaper do SystemUI), então RenderEffect não alcança; e o blur de
 * janela (FLAG_BLUR_BEHIND) está bloqueado pelo ROM deste aparelho. A saída é
 * desenhar nós mesmos uma cópia da imagem enquanto o drawer está aberto/arrastando
 * (XaulinXsWallpaperView) e borrar essa cópia.
 *
 * Limitações conhecidas:
 *  - Precisa conseguir LER o wallpaper: WallpaperManager.getDrawable() exige
 *    "Acesso a todos os arquivos" (MANAGE_EXTERNAL_STORAGE, já declarada no manifest,
 *    mesma permissão usada pelas fontes). Sem ela, a leitura falha em silêncio
 *    (log "XaulinXsSysWallpaper") e simplesmente não há desfoque nesse modo.
 *  - Wallpaper animado (live wallpaper) não tem imagem estática: sem desfoque.
 */
package com.xaulinxs.customizations.theme

import android.app.WallpaperManager
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.drawable.BitmapDrawable
import android.os.SystemClock
import android.util.Log
import com.android.launcher3.util.Executors

object XaulinXsSystemWallpaperSnapshot {
    private const val TAG = "XaulinXsSysWallpaper"
    private const val RETRY_AFTER_FAILURE_MS = 10_000L

    @Volatile private var bitmap: Bitmap? = null
    @Volatile private var loadedId = -1
    @Volatile private var loading = false
    @Volatile private var lastFailureAt = 0L

    /** Snapshot já carregado (ou null). Seguro de chamar em onDraw. */
    @JvmStatic
    fun peek(): Bitmap? = bitmap

    /**
     * Garante, em background, que o snapshot do wallpaper atual do sistema esteja
     * carregado. [onReady] roda na main thread quando um bitmap novo ficar pronto.
     */
    @JvmStatic
    fun ensureLoaded(context: Context, onReady: () -> Unit) {
        val app = context.applicationContext
        val wm = WallpaperManager.getInstance(app)
        val id = try {
            wm.getWallpaperId(WallpaperManager.FLAG_SYSTEM)
        } catch (e: Exception) {
            -1
        }
        if (bitmap != null && id == loadedId) return
        if (loading) return
        if (lastFailureAt != 0L &&
            SystemClock.elapsedRealtime() - lastFailureAt < RETRY_AFTER_FAILURE_MS
        ) return

        loading = true
        Executors.THREAD_POOL_EXECUTOR.execute {
            try {
                if (wm.wallpaperInfo != null) {
                    // Live wallpaper: não existe imagem estática confiável para borrar.
                    bitmap = null
                    loadedId = id
                    lastFailureAt = SystemClock.elapsedRealtime()
                    return@execute
                }
                val d = wm.drawable
                val bmp = when {
                    d == null -> null
                    d is BitmapDrawable -> d.bitmap
                    else -> {
                        val w = d.intrinsicWidth.coerceAtLeast(1)
                        val h = d.intrinsicHeight.coerceAtLeast(1)
                        Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888).also {
                            d.setBounds(0, 0, w, h)
                            d.draw(Canvas(it))
                        }
                    }
                }
                bitmap = bmp
                loadedId = id
                if (bmp != null) {
                    lastFailureAt = 0L
                    Executors.MAIN_EXECUTOR.execute(onReady)
                } else {
                    lastFailureAt = SystemClock.elapsedRealtime()
                }
            } catch (e: SecurityException) {
                lastFailureAt = SystemClock.elapsedRealtime()
                Log.w(TAG, "Sem permissão para ler o wallpaper do sistema " +
                    "(conceda 'Acesso a todos os arquivos' ao launcher)", e)
            } catch (e: Exception) {
                lastFailureAt = SystemClock.elapsedRealtime()
                Log.w(TAG, "Falha ao ler o wallpaper do sistema", e)
            } finally {
                loading = false
            }
        }
    }
}
