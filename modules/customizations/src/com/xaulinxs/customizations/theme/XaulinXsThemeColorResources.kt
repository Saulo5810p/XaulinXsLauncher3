/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * "UI-UX Custom Colors" — parte 2: interceptação em runtime.
 *
 * Como visto na investigação: reescrever res/values/material_dynamic_
 * colors_fallback.xml não é possível depois do APK instalado (recurso
 * empacotado em resources.arsc é somente leitura sem root). A solução
 * viável é interceptar a LEITURA da cor, não o arquivo: um ContextWrapper
 * (XaulinXsThemedContextWrapper, abaixo) instalado em cada Activity via
 * attachBaseContext (NÃO em LauncherApplication — isso quebrava
 * BroadcastReceiver, ver LauncherApplication.java) intercepta tanto
 * Context.getColor()/getColorStateList() quanto, via getResources(),
 * qualquer leitura feita através do Resources (inflação de XML,
 * Resources.getColor() direto). Isso cobre os drawable XML, layout XML
 * e código Kotlin/Java levantados, para os 30 IDs materialColorX/
 * customColorSurfaceEffect0 — sem tocar em nenhum dos ~46 arquivos
 * consumidores.
 */
package com.xaulinxs.customizations.theme

import android.content.Context
import android.content.ContextWrapper
import android.content.res.ColorStateList
import android.content.res.Resources
import android.util.SparseArray
import androidx.annotation.ColorInt

object XaulinXsThemeColorResources {

    private const val KEY_ENABLED = "xaulinxs_custom_colors_enabled"
    private const val KEY_PRIMARY = "xaulinxs_custom_colors_primary"
    private const val KEY_SECONDARY = "xaulinxs_custom_colors_secondary"

    // Seeds default: mesmas cores do roxo Material padrão do fallback
    // original (materialColorPrimary/#6750A4, materialColorSecondary/
    // #625B71), para que "desligado" e "nunca configurado" produzam o
    // mesmo visual de hoje.
    const val DEFAULT_PRIMARY: Int = 0xFF6750A4.toInt()
    const val DEFAULT_SECONDARY: Int = 0xFF625B71.toInt()

    @Volatile private var overrideMap: SparseArray<Int>? = null

    /** Preferências cruas (lidas/gravadas via LauncherPrefs pelas Preference screens). */
    fun isEnabled(context: Context): Boolean =
        prefs(context).getBoolean(KEY_ENABLED, false)

    fun getPrimarySeed(context: Context): Int =
        prefs(context).getInt(KEY_PRIMARY, DEFAULT_PRIMARY)

    fun getSecondarySeed(context: Context): Int =
        prefs(context).getInt(KEY_SECONDARY, DEFAULT_SECONDARY)

    /**
     * Salva as seeds, recalcula a paleta e ativa a interceptação. Chamado
     * pelos sliders da tela "UI-UX Custom Colors". As Activities/Views
     * abertas continuam com a cor antiga até recriar (mesmo comportamento
     * de qualquer troca de tema no Android) — por isso a tela de
     * configurações chama Activity.recreate() ao soltar o slider.
     */
    @JvmStatic
    fun applyAndSave(context: Context, @ColorInt primarySeed: Int, @ColorInt secondarySeed: Int) {
        prefs(context).edit()
            .putBoolean(KEY_ENABLED, true)
            .putInt(KEY_PRIMARY, primarySeed)
            .putInt(KEY_SECONDARY, secondarySeed)
            .apply()
        rebuildOverrideMap(context, primarySeed, secondarySeed)
    }

    @JvmStatic
    fun setEnabled(context: Context, enabled: Boolean) {
        prefs(context).edit().putBoolean(KEY_ENABLED, enabled).apply()
        if (enabled) {
            rebuildOverrideMap(context, getPrimarySeed(context), getSecondarySeed(context))
        } else {
            overrideMap = null
        }
    }

    /** Chamado uma vez em LauncherApplication.onCreate(), populando o mapa de override cedo. */
    @JvmStatic
    fun installIfEnabled(context: Context) {
        if (isEnabled(context)) {
            rebuildOverrideMap(context, getPrimarySeed(context), getSecondarySeed(context))
        }
    }

    private fun rebuildOverrideMap(context: Context, primarySeed: Int, secondarySeed: Int) {
        val palette = XaulinXsColorPalette.generate(primarySeed, secondarySeed)
        val resources = context.resources
        val pkg = context.packageName
        val map = SparseArray<Int>()
        for ((name, color) in palette.toMap()) {
            val id = resources.getIdentifier(name, "color", pkg)
            if (id != 0) {
                map.put(id, color)
            }
            // id == 0 significa que este nome não existe como @color/ neste
            // build (ex.: proguard/shrink removeu um recurso não usado por
            // nenhum arquivo em src_no_quickstep) — sem-op seguro, apenas
            // essa cor específica não é interceptada.
        }
        overrideMap = map
    }

    /** Usado pelo XaulinXsThemedResources — null quando a feature está desligada. */
    internal fun colorFor(resId: Int): Int? = overrideMap?.get(resId)

    private fun prefs(context: Context) =
        context.applicationContext.getSharedPreferences("xaulinxs_custom_colors", Context.MODE_PRIVATE)
}

/**
 * Resources que intercepta getColor()/getColorStateList() para os IDs
 * presentes no mapa de override de XaulinXsThemeColorResources, e delega
 * ao Resources original para qualquer outro id.
 */
class XaulinXsThemedResources(base: Resources) : Resources(
    base.assets, base.displayMetrics, base.configuration,
) {
    @ColorInt
    override fun getColor(id: Int): Int {
        XaulinXsThemeColorResources.colorFor(id)?.let { return it }
        return super.getColor(id)
    }

    @ColorInt
    override fun getColor(id: Int, theme: Theme?): Int {
        XaulinXsThemeColorResources.colorFor(id)?.let { return it }
        return super.getColor(id, theme)
    }

    override fun getColorStateList(id: Int): ColorStateList {
        XaulinXsThemeColorResources.colorFor(id)?.let { return ColorStateList.valueOf(it) }
        return super.getColorStateList(id)
    }

    override fun getColorStateList(id: Int, theme: Theme?): ColorStateList {
        XaulinXsThemeColorResources.colorFor(id)?.let { return ColorStateList.valueOf(it) }
        return super.getColorStateList(id, theme)
    }
}

/**
 * ContextWrapper que substitui getResources() pelo XaulinXsThemedResources
 * acima. Instalado nas 3 Activities (Launcher, SettingsActivity,
 * CustomColorsActivity), cada uma via seu attachBaseContext.
 *
 * XaulinXs fix: sobrescrever só getResources() não bastava — a maioria
 * do código real do Launcher3 chama context.getColor(R.color.materialColorX)
 * diretamente (ex.: AutomatedIconDelegate.kt, PreloadIconDelegate.kt),
 * não resources.getColor(id). Context.getColor()/getColorStateList()
 * em ContextWrapper são métodos que simplesmente delegam para o Context
 * "base" original (mBase.getColor(id)) — não passam por
 * this.getResources() — então a cor nunca era interceptada nesse
 * caminho, por isso "não aplicou em lugar nenhum" mesmo com o wrapper
 * instalado e sem nenhum crash. Fix: sobrescrever getColor()/
 * getColorStateList() aqui também, delegando para o Resources
 * interceptador em vez de para o base.
 *
 * Sem custo perceptível quando a feature está desligada: cada chamada
 * faz um único lookup em SparseArray nula (early return via colorFor()
 * retornando null) antes de delegar ao original.
 */
class XaulinXsThemedContextWrapper(base: Context) : ContextWrapper(base) {
    private val themedResources: Resources by lazy { XaulinXsThemedResources(base.resources) }

    override fun getResources(): Resources = themedResources

    @ColorInt
    override fun getColor(id: Int): Int {
        XaulinXsThemeColorResources.colorFor(id)?.let { return it }
        return super.getColor(id)
    }

    override fun getColorStateList(id: Int): ColorStateList {
        XaulinXsThemeColorResources.colorFor(id)?.let { return ColorStateList.valueOf(it) }
        return super.getColorStateList(id)
    }
}
