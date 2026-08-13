/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Storage + carregamento da fonte customizada (TTF/OTF) importada pelo
 * usuário via XaulinXsFontFileManagerActivity. Mesmo princípio do projeto
 * irmão XaulinXs LatinIME: guarda o CAMINHO INTERNO (já copiado para
 * filesDir/xaulinxs_fonts/ pelo próprio file manager), nunca o caminho
 * externo original, e cacheia o Typeface já carregado em memória — este
 * método é chamado no hot path de desenho de cada label de ícone.
 */
package com.xaulinxs.customizations.font

import android.content.Context
import android.graphics.Typeface
import android.util.Log
import com.android.launcher3.ConstantItem
import com.android.launcher3.EncryptionType
import com.android.launcher3.LauncherPrefs
import java.io.File

object XaulinXsCustomFont {

    private const val TAG = "XaulinXsCustomFont"

    // Sem backedUpItem() aqui de propósito: o default é null, e
    // ConstantItem deriva `type` de `defaultValue!!::class.java` por
    // padrão — com null isso daria NPE, então o `type` precisa ser
    // explícito (mesmo padrão usado em NON_FIXED_LANDSCAPE_GRID_NAME no
    // LauncherPrefs.kt original).
    val CUSTOM_FONT_PATH: ConstantItem<String?> = ConstantItem(
        sharedPrefKey = "xaulinxs_custom_font_path",
        isBackedUp = true,
        defaultValue = null,
        encryptionType = EncryptionType.ENCRYPTED,
        type = String::class.java,
    )

    @Volatile private var cachedTypeface: Typeface? = null
    @Volatile private var cachedTypefacePath: String? = null

    @JvmStatic
    fun getCustomFontPath(context: Context): String? =
        LauncherPrefs.get(context).get(CUSTOM_FONT_PATH)

    @JvmStatic
    fun setCustomFontPath(context: Context, path: String?) {
        LauncherPrefs.get(context).put(CUSTOM_FONT_PATH, path)
        cachedTypeface = null
        cachedTypefacePath = null
    }

    /**
     * Carrega a fonte customizada do disco, se configurada e o arquivo
     * ainda existir. Nunca lança exceção — quem chamar sempre pode recair
     * no Typeface padrão da view.
     */
    @JvmStatic
    fun loadTypefaceIfAvailable(context: Context): Typeface? {
        val path = getCustomFontPath(context)
        if (path == null) {
            cachedTypeface = null
            cachedTypefacePath = null
            return null
        }
        cachedTypeface?.let { if (path == cachedTypefacePath) return it }

        val file = File(path)
        if (!file.isFile) {
            Log.w(TAG, "Custom font file no longer exists: $path")
            cachedTypeface = null
            cachedTypefacePath = null
            return null
        }
        return try {
            val typeface = Typeface.createFromFile(file)
            cachedTypeface = typeface
            cachedTypefacePath = path
            typeface
        } catch (e: Exception) {
            Log.w(TAG, "Failed to load custom font from $path", e)
            cachedTypeface = null
            cachedTypefacePath = null
            null
        }
    }
}
