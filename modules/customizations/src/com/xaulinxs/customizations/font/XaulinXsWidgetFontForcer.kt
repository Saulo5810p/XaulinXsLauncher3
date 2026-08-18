/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Força a fonte customizada também dentro de widgets de terceiros
 * (RemoteViews de outros apps: Calendar, Gmail, etc). Abordagem
 * deliberadamente diferente da usada para os ícones/telas do próprio
 * launcher (XaulinXsGlobalFontInflaterFactory, hook na INFLAÇÃO via
 * LayoutInflater.Factory2): widgets de terceiros usam o Context do
 * PACOTE DO WIDGET durante a inflação (ver
 * XaulinXsGlobalFontInflaterFactory — é exatamente por isso que esse
 * Factory2 agora ignora esses contextos, para não quebrar a inflação
 * deles), então não há hook de inflação seguro e genérico disponível
 * para widgets de terceiros sem repetir o mesmo bug de estabilidade.
 *
 * Estratégia: pós-processamento na árvore de views JÁ INFLADA, depois
 * que o widget termina de carregar — mesmo ponto de entrada e mesmo
 * padrão já usado por XaulinXsWidgetBlur (ver
 * LauncherAppWidgetHostView.updateAppWidget, chamado logo após
 * super.updateAppWidget). Percorre recursivamente a árvore da
 * AppWidgetHostView e troca o typeface de toda TextView (e subclasses:
 * Button, EditText, Chronometer, etc.) encontrada.
 *
 * Limitação conhecida e aceita: RemoteViews pode reaplicar estilos
 * originais (incluindo typeface) em atualizações futuras do widget
 * (ex.: o próprio app de terceiro reenviando um RemoteViews novo via
 * AppWidgetManager.updateAppWidget) — isso sobrescreveria a fonte
 * forçada até a próxima chamada de updateAppWidget() do host, que é
 * exatamente quando applyTo() roda de novo. Não há forma de interceptar
 * isso de forma mais imediata sem hooks mais invasivos (reflection em
 * RemoteViews.OnClickHandler/RemoteViews internals) — fora de escopo
 * por ora.
 */
package com.xaulinxs.customizations.font

import android.view.View
import android.view.ViewGroup
import android.widget.TextView

object XaulinXsWidgetFontForcer {

    /**
     * Percorre [view] (tipicamente a raiz de uma AppWidgetHostView) e
     * aplica a fonte customizada configurada em toda TextView
     * encontrada na árvore. Sem-op silencioso se nenhuma fonte estiver
     * configurada (loadTypefaceIfAvailable retorna null nesse caso, e
     * aplicar null é seguro: reseta para o typeface original resolvido
     * pelo tema/XML da própria view, mesmo comportamento de reset já
     * usado em XaulinXsCustomFont.applyRecursively).
     */
    @JvmStatic
    fun applyTo(view: View) {
        val typeface = XaulinXsCustomFont.loadTypefaceIfAvailable(view.context)
        applyRecursively(view, typeface)
    }

    private fun applyRecursively(view: View, typeface: android.graphics.Typeface?) {
        if (view is TextView) {
            view.typeface = typeface
        }
        if (view is ViewGroup) {
            for (i in 0 until view.childCount) {
                applyRecursively(view.getChildAt(i), typeface)
            }
        }
    }
}
