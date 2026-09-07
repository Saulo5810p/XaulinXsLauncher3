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
     *
     * XaulinXs fix (crash real confirmado via logcat do Galaxy A35):
     * updateAppWidget() -- de onde applyTo() é chamado -- às vezes roda
     * fora da main thread. O caminho observado no crash:
     * AppWidgetHost.startListening() (chamado a partir de uma
     * HandlerThread interna, "UiThreadHelper", não a main thread) ->
     * updateAppWidgetView() -> ListenableHostView.updateAppWidget() ->
     * LauncherAppWidgetHostView.updateAppWidget() ->
     * XaulinXsWidgetFontForcer.applyTo(). TextView.setTypeface()
     * dispara requestLayout() internamente (troca de fonte pode mudar
     * as dimensões do texto), e View exige que só a thread que criou a
     * hierarquia toque nela -- CalledFromWrongThreadException.
     * (XaulinXsWidgetBlur.applyTo(), chamado na linha logo acima desta
     * no host, nunca teve esse problema: setRenderEffect() só marca a
     * view para redesenho com efeito diferente, não invalida layout.)
     *
     * Fix: agenda a aplicação de fato via View.post(), que sempre
     * entrega o Runnable na main thread (mesmo se a view ainda não
     * estiver anexada à janela nesse momento -- o Android enfileira
     * internamente e despacha assim que anexa). applyTo() em si
     * continua podendo ser chamado de qualquer thread com segurança.
     *
     * XaulinXs fix #2 (info.txt: "fonte customizada em widgets que
     * desaplica sozinha"): o applyRecursively() de antes só rodava no
     * instante do updateAppWidget() do host. Só isso não basta para
     * dois casos comuns que acontecem SEM um updateAppWidget() novo:
     *  1) widgets baseados em lista (RemoteViewsAdapter — ListView/
     *     GridView dentro do widget) criam/reciclam os TextViews de
     *     cada item sob demanda, conforme o usuário rola a lista —
     *     views que nem existiam ainda quando applyTo() rodou da
     *     primeira vez, então nunca recebiam a fonte;
     *  2) o próprio RemoteViews reaplica os estilos originais de um
     *     TextView em qualquer atualização parcial subsequente (ex.:
     *     relógio/clima atualizando só o texto a cada minuto), o que
     *     também dispara uma nova passada de layout na view.
     * Os dois casos têm uma coisa em comum: sempre geram uma passada
     * de layout na hierarquia do widget. Por isso, além da aplicação
     * pontual, registramos (uma única vez por hierarquia) um
     * OnGlobalLayoutListener na raiz que reaplica a fonte a cada
     * passada de layout futura — sem precisar de um updateAppWidget()
     * novo do host. Para não entrar em loop infinito (setTypeface()
     * também dispara requestLayout(), que dispararia o próprio
     * listener de novo), applyRecursively() só toca na TextView quando
     * o typeface atual já é diferente do desejado.
     *
     * O controle de "já registrei o listener pra essa view" usa um
     * WeakHashMap (chave fraca — não impede a AppWidgetHostView de ser
     * coletada quando o widget é removido) em vez de View.setTag(int,
     * Object): esse overload de setTag exige uma resource id de
     * verdade como chave (lança IllegalArgumentException fora desse
     * intervalo), então uma chave arbitrária aqui seria arriscada.
     */
    private val viewsWithReapplyListener =
        java.util.Collections.newSetFromMap(java.util.WeakHashMap<View, Boolean>())

    @JvmStatic
    fun applyTo(view: View) {
        view.post {
            applyRecursively(view, XaulinXsCustomFont.loadTypefaceIfAvailable(view.context))
        }
        registerGlobalLayoutReapplier(view)
    }

    private fun registerGlobalLayoutReapplier(root: View) {
        synchronized(viewsWithReapplyListener) {
            if (!viewsWithReapplyListener.add(root)) return
        }
        root.viewTreeObserver.addOnGlobalLayoutListener {
            if (!root.isAttachedToWindow) return@addOnGlobalLayoutListener
            applyRecursively(root, XaulinXsCustomFont.loadTypefaceIfAvailable(root.context))
        }
    }

    private fun applyRecursively(view: View, typeface: android.graphics.Typeface?) {
        if (view is TextView && view.typeface !== typeface) {
            view.typeface = typeface
        }
        if (view is ViewGroup) {
            for (i in 0 until view.childCount) {
                applyRecursively(view.getChildAt(i), typeface)
            }
        }
    }
}
