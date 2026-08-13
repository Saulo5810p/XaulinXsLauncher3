/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Recorta a região real do wallpaper que fica atrás de uma View na tela,
 * pra servir de fundo borrado da barra de busca. Protegido com try/catch
 * total: se WallpaperManager.getDrawable() falhar por qualquer motivo
 * (sem MANAGE_EXTERNAL_STORAGE, wallpaper animado sem bitmap estático,
 * ROM sem suporte), retorna null e o chamador cai de volta pra cor
 * translúcida sozinha, sem crash.
 *
 * O blur em si NÃO é feito aqui: é aplicado depois via
 * View.setRenderEffect() na ImageView que recebe este bitmap (API 31+) —
 * mesmo princípio do blur real do App Drawer (XaulinXsDepthController),
 * só que numa imagem estática em vez da workspace/hotseat ao vivo.
 */
package com.xaulinxs.customizations.search

import android.app.WallpaperManager
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.drawable.Drawable
import android.util.Log
import android.view.View

private const val TAG = "XaulinXsSearchBarBlur"

object XaulinXsSearchBarBlur {

    fun getWallpaperBackdropBitmap(context: Context, target: View): Bitmap? {
        return try {
            val metrics = target.resources.displayMetrics
            val screenWidth = metrics.widthPixels
            val screenHeight = metrics.heightPixels

            val wallpaperDrawable: Drawable =
                WallpaperManager.getInstance(context).drawable ?: return null
            val wallpaperWidth = wallpaperDrawable.intrinsicWidth
            val wallpaperHeight = wallpaperDrawable.intrinsicHeight
            if (wallpaperWidth <= 0 || wallpaperHeight <= 0) return null
            if (target.width <= 0 || target.height <= 0) return null

            val scale = maxOf(
                screenWidth.toFloat() / wallpaperWidth,
                screenHeight.toFloat() / wallpaperHeight,
            )
            val offsetX = (wallpaperWidth * scale - screenWidth) / 2f
            val offsetY = (wallpaperHeight * scale - screenHeight) / 2f

            val location = IntArray(2)
            target.getLocationOnScreen(location)

            val cropLeft = (location[0] + offsetX) / scale
            val cropTop = (location[1] + offsetY) / scale
            val cropWidth = target.width / scale
            val cropHeight = target.height / scale
            if (cropWidth <= 0f || cropHeight <= 0f) return null

            val output = Bitmap.createBitmap(target.width, target.height, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(output)
            canvas.scale(target.width / cropWidth, target.height / cropHeight)
            canvas.translate(-cropLeft, -cropTop)
            wallpaperDrawable.setBounds(0, 0, wallpaperWidth, wallpaperHeight)
            wallpaperDrawable.draw(canvas)
            output
        } catch (e: SecurityException) {
            Log.w(TAG, "Sem permissão para ler o wallpaper real", e)
            null
        } catch (e: Exception) {
            Log.w(TAG, "Falha ao recortar o wallpaper para a barra de busca", e)
            null
        }
    }
}
