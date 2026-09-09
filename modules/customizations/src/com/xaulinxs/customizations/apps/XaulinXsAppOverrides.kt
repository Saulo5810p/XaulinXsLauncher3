/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Persistência central dos "overrides" que o usuário define no popup de app
 * (Fase 2/3/4): nome renomeado, ícone customizado (imagem própria escolhida
 * na galeria) e "esconder do menu de aplicativos". Um único registro por
 * componente (pacote+atividade), guardado como JSON dentro de UM item
 * backed-up de LauncherPrefs (mesmo padrão de ALL_APPS_TIP_SHOWN_TIMESTAMPS,
 * que também guarda uma lista serializada como String) — evita criar uma
 * chave de SharedPreferences por app instalado.
 *
 * Ícones customizados são bitmaps decodificados a partir da imagem que o
 * usuário escolheu, salvos como PNG em arquivo próprio (não cabe/não faz
 * sentido guardar bytes de imagem dentro do JSON de preferências), e o JSON
 * guarda só o nome do arquivo.
 */
package com.xaulinxs.customizations.apps

import android.content.ComponentName
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Log
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem
import com.android.launcher3.util.Executors
import java.io.File
import java.io.FileOutputStream
import org.json.JSONException
import org.json.JSONObject

/** Um override guardado pra um componente (app) específico. */
data class XaulinXsAppOverride(
    val customName: String? = null,
    val customIconFile: String? = null,
    val hidden: Boolean = false,
)

object XaulinXsAppOverrides {
    private const val TAG = "XaulinXsAppOverrides"
    private const val KEY_OVERRIDES_JSON = "xaulinxs_app_overrides_json"
    private const val ICON_DIR = "xaulinxs_app_icons"

    private val OVERRIDES_JSON = backedUpItem(KEY_OVERRIDES_JSON, "")

    /**
     * Notificado sempre que um override é gravado (nome, ícone ou esconder), com o
     * componente afetado. Usado pra refletir a mudança na hora - em especial o ícone,
     * que é salvo em background thread pela AppIconPickerActivity e pode terminar
     * depois que o popup que iniciou a troca já fechou.
     */
    private val listeners = mutableListOf<(ComponentName) -> Unit>()

    @JvmStatic
    fun addOnChangedListener(listener: (ComponentName) -> Unit) {
        listeners.add(listener)
    }

    @JvmStatic
    fun removeOnChangedListener(listener: (ComponentName) -> Unit) {
        listeners.remove(listener)
    }

    private fun notifyChanged(componentName: ComponentName) {
        Executors.MAIN_EXECUTOR.execute { listeners.forEach { it(componentName) } }
    }

    /**
     * Lê todos os overrides do JSON persistido. Chamadas malformadas (versão antiga
     * corrompida, edição manual etc.) resultam em mapa vazio em vez de crash - overrides
     * são uma conveniência visual, nunca devem quebrar o launcher se o dado for inválido.
     */
    private fun readAll(context: Context): MutableMap<String, XaulinXsAppOverride> {
        val raw = LauncherPrefs.get(context).get(OVERRIDES_JSON)
        if (raw.isBlank()) return mutableMapOf()
        val result = mutableMapOf<String, XaulinXsAppOverride>()
        try {
            val root = JSONObject(raw)
            root.keys().forEach { key ->
                val entry = root.getJSONObject(key)
                result[key] =
                    XaulinXsAppOverride(
                        customName = entry.optString("name", "").ifBlank { null },
                        customIconFile = entry.optString("icon", "").ifBlank { null },
                        hidden = entry.optBoolean("hidden", false),
                    )
            }
        } catch (e: JSONException) {
            Log.w(TAG, "Overrides JSON corrompido, ignorando (nenhum override será aplicado)", e)
            return mutableMapOf()
        }
        return result
    }

    private fun writeAll(context: Context, overrides: Map<String, XaulinXsAppOverride>) {
        val root = JSONObject()
        overrides.forEach { (key, override) ->
            if (
                override.customName == null && override.customIconFile == null &&
                    !override.hidden
            ) {
                // Entrada vazia - não vale a pena persistir, mantém o JSON enxuto.
                return@forEach
            }
            val entry = JSONObject()
            override.customName?.let { entry.put("name", it) }
            override.customIconFile?.let { entry.put("icon", it) }
            entry.put("hidden", override.hidden)
            root.put(key, entry)
        }
        LauncherPrefs.get(context).put(OVERRIDES_JSON.to(root.toString()))
    }

    private fun keyFor(componentName: ComponentName): String = componentName.flattenToString()

    @JvmStatic
    fun get(context: Context, componentName: ComponentName?): XaulinXsAppOverride? {
        if (componentName == null) return null
        return readAll(context)[keyFor(componentName)]
    }

    @JvmStatic
    fun isHidden(context: Context, componentName: ComponentName?): Boolean =
        get(context, componentName)?.hidden == true

    /** Retorna o conjunto de todos os componentes atualmente escondidos. */
    @JvmStatic
    fun hiddenComponents(context: Context): Set<String> =
        readAll(context).filterValues { it.hidden }.keys

    @JvmStatic
    fun setHidden(context: Context, componentName: ComponentName, hidden: Boolean) {
        val all = readAll(context)
        val key = keyFor(componentName)
        val current = all[key] ?: XaulinXsAppOverride()
        all[key] = current.copy(hidden = hidden)
        writeAll(context, all)
        notifyChanged(componentName)
    }

    @JvmStatic
    fun setCustomName(context: Context, componentName: ComponentName, name: String?) {
        val all = readAll(context)
        val key = keyFor(componentName)
        val current = all[key] ?: XaulinXsAppOverride()
        all[key] = current.copy(customName = name?.trim()?.ifBlank { null })
        writeAll(context, all)
        notifyChanged(componentName)
    }

    /**
     * Salva [bitmap] como o ícone customizado do componente e persiste a referência.
     * Sobrescreve/apaga o arquivo anterior desse componente, se existir, pra não acumular
     * lixo em disco a cada troca de ícone.
     */
    @JvmStatic
    fun setCustomIcon(context: Context, componentName: ComponentName, bitmap: Bitmap) {
        val all = readAll(context)
        val key = keyFor(componentName)
        val current = all[key] ?: XaulinXsAppOverride()
        current.customIconFile?.let { deleteIconFile(context, it) }

        val fileName = "icon_${key.hashCode()}_${System.currentTimeMillis()}.png"
        val dir = iconDir(context)
        dir.mkdirs()
        try {
            FileOutputStream(File(dir, fileName)).use { out ->
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Falha ao salvar ícone customizado para $key", e)
            return
        }

        all[key] = current.copy(customIconFile = fileName)
        writeAll(context, all)
        notifyChanged(componentName)
    }

    @JvmStatic
    fun clearCustomIcon(context: Context, componentName: ComponentName) {
        val all = readAll(context)
        val key = keyFor(componentName)
        val current = all[key] ?: return
        current.customIconFile?.let { deleteIconFile(context, it) }
        all[key] = current.copy(customIconFile = null)
        writeAll(context, all)
        notifyChanged(componentName)
    }

    @JvmStatic
    fun loadCustomIconBitmap(context: Context, fileName: String): Bitmap? {
        val file = File(iconDir(context), fileName)
        if (!file.exists()) return null
        return try {
            BitmapFactory.decodeFile(file.absolutePath)
        } catch (e: Exception) {
            Log.e(TAG, "Falha ao carregar ícone customizado de $fileName", e)
            null
        }
    }

    private fun deleteIconFile(context: Context, fileName: String) {
        try {
            File(iconDir(context), fileName).delete()
        } catch (e: Exception) {
            Log.w(TAG, "Falha ao apagar ícone customizado antigo $fileName", e)
        }
    }

    private fun iconDir(context: Context): File = File(context.filesDir, ICON_DIR)
}
