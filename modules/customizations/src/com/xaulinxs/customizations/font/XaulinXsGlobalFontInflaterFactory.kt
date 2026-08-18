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
        // XaulinXs fix v2 (causa raiz REAL confirmada via logcat real do
        // Galaxy A35, não só leitura estática de código — a hipótese
        // anterior, "não participar quando um ancestral já anexado é
        // AppWidgetHostView", nunca disparava: durante rInflateChildren()
        // a view sendo inflada ainda não está anexada a nenhum
        // AppWidgetHostView, então esse ancestral nunca existe no
        // momento em que onCreateView roda, e o Factory2 participava do
        // mesmo jeito.
        //
        // O log real mostrou: RemoteViews.inflateView() (widget do
        // Calendar, com.android.calendar:layout/appwidget) chama
        // LayoutInflater.inflate() com ESTE Factory2 instalado (visível
        // na stacktrace: XaulinXsGlobalFontInflaterFactory.onCreateView
        // -> createViewFallback). createViewFallback usa
        // inflater.createView(name, prefix, attrs), um caminho de
        // resolução mais limitado que o inflater padrão: ao construir a
        // view raiz do widget (LinearLayout), o construtor de View
        // resolve um atributo de tema (actionBarTheme) que aponta para
        // um drawable-animator do PRÓPRIO launcher
        // (design_fab_hide_motion_spec) só que resolvido no contexto/
        // classloader do pacote do Calendar -- Resources$NotFoundException
        // seguido de ClassNotFoundException ao tentar inflar a tag
        // <set> desse animator. Não é um problema de tag XML isolada; é
        // o contexto errado (tema do launcher vazando para dentro da
        // inflação de RemoteViews de outro pacote) sendo usado para
        // resolver um atributo de tema durante a construção da view.
        //
        // Fix real: nunca participar quando o Context da inflação não é
        // o do PRÓPRIO pacote do launcher. RemoteViews sempre infla
        // usando o Context do pacote do app dono do widget (Calendar,
        // Gmail, etc, nunca "com.android.launcher3") -- então essa
        // checagem cobre QUALQUER inflação de RemoteViews de QUALQUER
        // app de terceiro, não só quando está dentro de um
        // AppWidgetHostView já anexado. Também cobre, pelo mesmo
        // motivo, qualquer outro Context de pacote externo que por
        // ventura passe por este Factory2 (ex.: notificações
        // customizadas, outros usos de RemoteViews fora de widgets).
        if (context.packageName != LAUNCHER_PACKAGE_NAME) {
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
        // O applicationId real do build (ver build.gradle:
        // applicationId "com.android.launcher3"). Hardcoded em vez de
        // BuildConfig.APPLICATION_ID porque BuildConfig ainda não é
        // usado em nenhum outro ponto deste módulo -- evita depender de
        // uma classe gerada cujo pacote pode variar conforme a variante
        // de build configurada no futuro.
        private const val LAUNCHER_PACKAGE_NAME = "com.android.launcher3"

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
