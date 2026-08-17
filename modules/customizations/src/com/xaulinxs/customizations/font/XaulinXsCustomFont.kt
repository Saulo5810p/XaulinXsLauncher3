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
import android.widget.TextView
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
        // XaulinXs fix: LauncherPrefs.put() espera Pair<Item, Any> (valor
        // não-nulo) — path nulo (ação "Restaurar padrão") precisa usar
        // remove(), não put() com null, senão o compilador rejeita e,
        // pior, o valor antigo nunca seria de fato limpo.
        val prefs = LauncherPrefs.get(context)
        if (path != null) {
            prefs.put(CUSTOM_FONT_PATH to path)
        } else {
            prefs.remove(CUSTOM_FONT_PATH)
        }
        cachedTypeface = null
        cachedTypefacePath = null
    }

    /**
     * Carrega a fonte customizada do disco, se configurada e o arquivo
     * ainda existir. Nunca lança exceção — quem chamar sempre pode recair
     * no Typeface padrão da view.
     */
    /**
     * XaulinXs fix (causa raiz do "fonte não muda ao importar"): o
     * typeface só era aplicado uma vez, no construtor de cada
     * BubbleTextView — views já existentes na tela nunca eram
     * recarregadas ao importar uma fonte nova. Este método percorre a
     * árvore de views a partir da raiz do launcher (Workspace, Hotseat,
     * AllApps — todos filhos da DragLayer) e reaplica o typeface atual
     * (ou o padrão do sistema, se a fonte foi resetada) em toda
     * BubbleTextView viva, sem precisar recriar a Activity.
     */
    @JvmStatic
    fun reapplyToVisibleIcons(context: Context, root: android.view.View) {
        val typeface = loadTypefaceIfAvailable(context)
        applyRecursively(root, typeface)
    }

    private fun applyRecursively(view: android.view.View, typeface: Typeface?) {
        // Restrito a BubbleTextView (ícones), nunca TextView genérico —
        // widgets, relógios, textos de notificação etc. NÃO devem ter o
        // typeface trocado por esta rotina. Reset usa null (não
        // Typeface.DEFAULT): null faz o Android resolver de volta o
        // fontFamily definido no tema/XML original da view (fontes
        // variáveis do Material), enquanto DEFAULT forçaria Roboto puro
        // e quebraria o visual original dos ícones.
        if (view is com.android.launcher3.BubbleTextView) {
            view.typeface = typeface
        }
        if (view is android.view.ViewGroup) {
            for (i in 0 until view.childCount) {
                applyRecursively(view.getChildAt(i), typeface)
            }
        }
    }

    /**
     * XaulinXs fix: o item "XaulinXs Customizations" na lista de
     * preferences (título/summary de uma PreferenceScreen aninhada) não
     * é alcançado de forma confiável por
     * XaulinXsGlobalFontInflaterFactory — PreferenceFragmentCompat
     * infla sua RecyclerView via um LayoutInflater CLONADO
     * (inflater.cloneInContext), e o PreferenceGroupAdapter que
     * desenha/recicla cada linha resolve o inflater a partir do Context
     * do ViewGroup pai da RecyclerView, nem sempre o mesmo Factory2
     * instalado em SettingsActivity.attachBaseContext.
     *
     * Fix: registra um listener na RecyclerView que aplica o typeface
     * diretamente em título/summary de cada item anexado — cobre tanto
     * o bind inicial quanto reciclagem durante scroll (diferente de uma
     * aplicação única, que perderia os itens reciclados depois).
     * Chamado do onCreatePreferences do fragment, depois que a
     * RecyclerView já existe.
     */
    @JvmStatic
    fun applyToPreferenceListRecycling(recyclerView: androidx.recyclerview.widget.RecyclerView) {
        recyclerView.addOnChildAttachStateChangeListener(
            object : androidx.recyclerview.widget.RecyclerView.OnChildAttachStateChangeListener {
                override fun onChildViewAttachedToWindow(view: android.view.View) {
                    val typeface = loadTypefaceIfAvailable(view.context)
                    val title = view.findViewById<android.view.View>(android.R.id.title)
                    if (title is TextView) title.typeface = typeface
                    val summary = view.findViewById<android.view.View>(android.R.id.summary)
                    if (summary is TextView) summary.typeface = typeface
                }

                override fun onChildViewDetachedFromWindow(view: android.view.View) = Unit
            },
        )
    }

    /**
     * XaulinXs fix: o título da tela de Configurações não é alcançado
     * por XaulinXsGlobalFontInflaterFactory porque nunca é inflado como
     * TextView a partir de XML — é desenhado/gerenciado internamente
     * pela própria Toolbar/CollapsingToolbarLayout. Chamado do onCreate
     * de SettingsActivity, depois de setContentView()+setActionBar().
     * Cobre os dois layouts possíveis (res/layout e res/layout-v31) sem
     * reflection, usando só API pública de cada view.
     */
    @JvmStatic
    fun applyToSettingsTitle(activity: android.app.Activity) {
        val typeface = loadTypefaceIfAvailable(activity)

        // Caso API 31+ (res/layout-v31/settings_activity.xml): o título
        // é desenhado pelo CollapsingToolbarLayout, não pela Toolbar em
        // si. Cobre título expandido e colapsado — são dois
        // TextPaint/Typeface independentes na CollapsingTextHelper.
        val collapsingToolbar = activity.findViewById<
            com.google.android.material.appbar.CollapsingToolbarLayout>(
            com.android.launcher3.R.id.collapsing_toolbar,
        )
        if (collapsingToolbar != null) {
            val resolved = typeface ?: android.graphics.Typeface.DEFAULT
            collapsingToolbar.setExpandedTitleTypeface(resolved)
            collapsingToolbar.setCollapsedTitleTypeface(resolved)
            return
        }

        // Caso pré-API 31 (res/layout/settings_activity.xml): Toolbar
        // simples sem CollapsingToolbarLayout. Toolbar não expõe API
        // pública de typeface do título, mas percorrer seus filhos
        // diretos e achar a TextView é seguro e documentado como padrão
        // (a própria Toolbar cria essa TextView internamente como filha
        // direta quando setTitle() é chamado) — sem reflection.
        val toolbar = activity.findViewById<android.widget.Toolbar>(
            com.android.launcher3.R.id.action_bar,
        ) ?: return
        for (i in 0 until toolbar.childCount) {
            val child = toolbar.getChildAt(i)
            if (child is TextView && child.text == activity.title) {
                child.typeface = typeface
                break
            }
        }
    }

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
