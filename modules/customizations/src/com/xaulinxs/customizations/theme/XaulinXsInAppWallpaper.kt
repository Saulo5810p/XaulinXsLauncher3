/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Feature nova (info.txt/etapa 3, decisão do usuário no chat): o
 * "R's Home3" agora tem um wallpaper PRÓPRIO, desenhado por uma View
 * nossa (ver XaulinXsWallpaperView) e guardado em armazenamento privado
 * do app — sem nunca tocar no wallpaper real do sistema
 * (WallpaperManager), A NÃO SER que o usuário troque de wallpaper
 * diretamente por dentro do nosso launcher (nesse caso sim, o pedido
 * original ("aí sim o papel de parede do sistema e do Launcher mudam")
 * é respeitado e propagamos pro sistema também).
 *
 * TRADE-OFFS aceitos nesta abordagem (documentados também no
 * NOTAS_ETAPA3B.md da entrega):
 *  1) Sem parallax de rolagem: o wallpaper de sistema recebe comandos de
 *     scroll (WallpaperOffsetInterpolator, já existente no AOSP) que só
 *     fazem sentido pra live wallpapers/imagens grandes controladas pelo
 *     WallpaperManager. Nosso wallpaper é uma imagem estática nossa,
 *     desenhada localmente — por ora sem parallax.
 *  2) Sem suporte a live wallpaper como plano de fundo do launcher — só
 *     imagem estática.
 *  3) [ATUALIZADO — já resolvido] A extração de cor pra ícones
 *     temáticos/scrim/balões passou a vir do NOSSO wallpaper — ver
 *     WallpaperColorHints.kt (com.android.launcher3.util), que agora
 *     prioriza WallpaperColors.fromBitmap(getCurrentWallpaper()) sobre a
 *     cor real do sistema. Ou seja, o pipeline de tema já está unificado
 *     com este arquivo.
 */
package com.xaulinxs.customizations.theme

import android.app.WallpaperManager
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.util.Log
import com.android.launcher3.util.Executors
import java.io.File
import java.io.FileOutputStream
import java.util.concurrent.CopyOnWriteArrayList

private const val TAG = "XaulinXsInAppWallpaper"
private const val DEFAULT_ASSET_NAME = "default_wallpaper.png"
private const val STORED_FILE_NAME = "xaulinxs_wallpaper.png"

/**
 * Fonte de verdade do wallpaper mostrado DENTRO do R's Home3. Nunca lê nem
 * escreve o wallpaper do sistema, exceto quando explicitamente pedido via
 * [setWallpaperFromUri] com `alsoUpdateSystemWallpaper = true`.
 */
object XaulinXsInAppWallpaper {

    @Volatile private var cachedBitmap: Bitmap? = null
    private val listeners = CopyOnWriteArrayList<() -> Unit>()

    /** Chamado uma vez, na criação do app (ver XaulinXsCustomizationsBootstrap). */
    @JvmStatic
    fun ensureDefaultWallpaperExists(context: Context) {
        val file = storedFile(context)
        if (file.exists()) return
        Executors.THREAD_POOL_EXECUTOR.execute {
            try {
                context.assets.open(DEFAULT_ASSET_NAME).use { input ->
                    FileOutputStream(file).use { output -> input.copyTo(output) }
                }
                Log.d(TAG, "Wallpaper padrão do R's Home3 copiado para armazenamento privado")
                notifyChanged()
            } catch (e: Exception) {
                Log.w(TAG, "Não foi possível preparar o wallpaper padrão do launcher", e)
            }
        }
    }

    /** Bitmap atual (cacheado em memória). Pode ser null no 1º frame, antes do arquivo existir. */
    @JvmStatic
    fun getCurrentWallpaper(context: Context): Bitmap? {
        cachedBitmap?.let { return it }
        val file = storedFile(context)
        if (!file.exists()) return null
        return try {
            BitmapFactory.decodeFile(file.absolutePath)?.also { cachedBitmap = it }
        } catch (e: Exception) {
            Log.w(TAG, "Falha ao decodificar o wallpaper do launcher", e)
            null
        }
    }

    /**
     * Troca o wallpaper do launcher a partir de uma imagem escolhida pelo usuário
     * (fluxo "Trocar wallpaper" dentro do R's Home3). [alsoUpdateSystemWallpaper]
     * deve ser true sempre que a troca partiu de uma ação explícita do usuário
     * dentro do nosso launcher — é exatamente essa a condição pedida no
     * info.txt pra também atualizar o wallpaper do sistema.
     */
    @JvmStatic
    fun setWallpaperFromUri(context: Context, uri: Uri, alsoUpdateSystemWallpaper: Boolean) {
        Executors.THREAD_POOL_EXECUTOR.execute {
            try {
                val bitmap = context.contentResolver.openInputStream(uri)?.use { input ->
                    BitmapFactory.decodeStream(input)
                } ?: return@execute

                FileOutputStream(storedFile(context)).use { output ->
                    bitmap.compress(Bitmap.CompressFormat.PNG, 100, output)
                }
                cachedBitmap = bitmap
                notifyChanged()

                if (alsoUpdateSystemWallpaper) {
                    WallpaperManager.getInstance(context).setBitmap(bitmap)
                }
            } catch (e: Exception) {
                Log.w(TAG, "Não foi possível trocar o wallpaper do launcher", e)
            }
        }
    }

    /** Views que precisam se redesenhar quando o wallpaper mudar (ex.: XaulinXsWallpaperView). */
    @JvmStatic
    fun addOnChangedListener(listener: () -> Unit) {
        listeners.add(listener)
    }

    @JvmStatic
    fun removeOnChangedListener(listener: () -> Unit) {
        listeners.remove(listener)
    }

    private fun notifyChanged() {
        Executors.MAIN_EXECUTOR.execute { listeners.forEach { it() } }
    }

    private fun storedFile(context: Context): File = File(context.filesDir, STORED_FILE_NAME)
}
