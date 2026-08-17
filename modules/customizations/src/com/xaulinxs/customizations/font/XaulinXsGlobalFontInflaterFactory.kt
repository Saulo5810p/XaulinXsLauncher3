/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Estende a fonte customizada (que já funcionava só para os labels dos
 * ícones via BubbleTextView) para TODA TextView do app — telas de
 * configurações, popups, diálogos, widget picker (View System), e
 * qualquer view nova que venha a ser inflada, sem precisar tocar em
 * cada estilo XML individualmente.
 *
 * Mecanismo: LayoutInflater.Factory2 é o hook oficial do Android para
 * interceptar toda inflação de view a partir de XML. Diferente de
 * sobrescrever fontFamily em cada @style, isso pega qualquer TextView
 * (ou subclasse: Button, EditText, CheckBox etc herdam de TextView)
 * automaticamente, incluindo layouts que ainda não existem hoje.
 *
 * Retornar null em onCreateView() deixa o LayoutInflater seguir seu
 * fluxo normal de criação (mesmo padrão usado em
 * LauncherPreviewRenderer.onCreateView para "fragment"/TextClock) —
 * aqui em vez de interceptar a criação em si, deixamos o inflater base
 * criar a view do jeito padrão e só aplicamos o typeface DEPOIS, o que
 * é mais seguro: preserva 100% do comportamento original de inflação
 * (estilos, temas, AppCompat quando aplicável) e só acrescenta uma
 * etapa no final.
 */
package com.xaulinxs.customizations.font

import android.appwidget.AppWidgetHostView
import android.content.Context
import android.util.AttributeSet
import android.view.LayoutInflater
import android.view.View
import android.widget.TextView

class XaulinXsGlobalFontInflaterFactory(
    private val baseFactory: LayoutInflater.Factory2?,
) : LayoutInflater.Factory2 {

    override fun onCreateView(
        parent: View?,
        name: String,
        context: Context,
        attrs: AttributeSet,
    ): View? {
        // XaulinXs fix (causa raiz dos widgets quebrados na Fase 2): a
        // Activity Launcher passa "this" como Context para
        // LauncherWidgetHolder/LauncherAppWidgetHost, então
        // AppWidgetHostView.updateAppWidget()/RemoteViews.apply() acaba
        // usando LayoutInflater.from(context) do MESMO LayoutInflater da
        // Activity — o que já tem este Factory2 instalado — em vez de um
        // inflater isolado do processo do widget, como a suposição
        // original (Fase 2) previa. RemoteViews.apply() já instala seu
        // próprio LayoutInflater.Filter (a própria RemoteViews via
        // onLoadClass) nesse mesmo inflater compartilhado para
        // sandboxing de segurança — nosso Factory2 rodando no meio disso
        // corrompe esse fluxo e quebra a inflação de QUALQUER widget.
        // Fix: se algum ancestral na árvore de "parent" for um
        // AppWidgetHostView, este Factory2 não participa em nada —
        // devolve null imediatamente e deixa o LayoutInflater original
        // resolver sozinho, do jeito que resolveria sem este Factory2
        // existir.
        if (isInsideAppWidgetHostView(parent)) {
            return null
        }

        // Deixa qualquer factory pré-existente (ex.: a própria do
        // PreferenceFragmentCompat/androidx) criar a view primeiro, se
        // houver uma; senão cai no inflater padrão da plataforma via
        // createView, que resolve o nome da tag (com ou sem pacote,
        // como "TextView" ou "com.android.launcher3.BubbleTextView").
        val view = baseFactory?.onCreateView(parent, name, context, attrs)
            ?: createViewFallback(context, name, attrs)

        applyFontIfTextView(context, view)
        return view
    }

    override fun onCreateView(name: String, context: Context, attrs: AttributeSet): View? =
        onCreateView(null, name, context, attrs)

    private fun isInsideAppWidgetHostView(parent: View?): Boolean {
        var current = parent
        while (current != null) {
            if (current is AppWidgetHostView) return true
            current = current.parent as? View
        }
        return false
    }

    private fun createViewFallback(context: Context, name: String, attrs: AttributeSet): View? {
        // createView(name, prefix, attrs) resolve a classe via reflection
        // diretamente (Class.forName), SEM reconsultar nenhuma Factory —
        // é o mesmo método que o PhoneLayoutInflater usa internamente
        // depois que nenhuma factory registrada resolveu a view, então é
        // seguro chamar daqui sem risco de recursão.
        val inflater = LayoutInflater.from(context)
        return try {
            if (name.contains('.')) {
                // Nome totalmente qualificado (ex.: view customizada do
                // launcher, como com.android.launcher3.BubbleTextView).
                inflater.createView(name, null, attrs)
            } else {
                // Nome de widget de plataforma sem pacote (ex.: "TextView",
                // "Button") — tenta os prefixos padrão nesta ordem, igual
                // o PhoneLayoutInflater faz internamente.
                for (prefix in PLATFORM_VIEW_PREFIXES) {
                    try {
                        return inflater.createView(name, prefix, attrs)
                    } catch (e: ClassNotFoundException) {
                        // tenta o próximo prefixo
                    }
                }
                null
            }
        } catch (e: ClassNotFoundException) {
            // Não é um widget conhecido por esses caminhos (ex.: tags
            // estruturais como <merge>/<include>, ou uma view customizada
            // fora do padrão android.widget) — devolve null e deixa o
            // LayoutInflater original (chamado por fora desta factory)
            // resolver do jeito dele.
            null
        }
    }

    private fun applyFontIfTextView(context: Context, view: View?) {
        if (view !is TextView) return
        // loadTypefaceIfAvailable retorna null quando não há fonte
        // customizada configurada — nesse caso não fazemos nada e a
        // view fica com o typeface que o tema/estilo XML já aplicou
        // normalmente (comportamento 100% original preservado).
        val typeface = XaulinXsCustomFont.loadTypefaceIfAvailable(context) ?: return
        view.typeface = typeface
    }

    companion object {
        // Mesma ordem de prefixos que o PhoneLayoutInflater da plataforma
        // tenta internamente ao resolver uma tag sem pacote.
        private val PLATFORM_VIEW_PREFIXES = arrayOf(
            "android.widget.",
            "android.webkit.",
            "android.app.",
            "android.view.",
        )
    }
}
