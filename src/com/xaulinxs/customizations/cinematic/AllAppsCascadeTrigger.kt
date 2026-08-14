/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Substitui a versão anterior (AllAppsEnterCascadeState, baseada numa
 * janela de tempo única) por detecção de MUDANÇA DE DIREÇÃO: dispara o
 * giro 720° em cascata (AllAppsIconEnterEffect) toda vez que o gesto de
 * abrir/fechar o app drawer inverte de sentido — inclusive no meio do
 * caminho, sem precisar o drawer estar 100% fechado ou 100% aberto antes.
 * Isso corrige o problema relatado: abrindo/fechando repetidamente rápido,
 * o efeito quase nunca disparava porque a janela antiga só ativava quando
 * o progresso cruzava 0.98 vindo de cima — na prática, quase nunca
 * acontecia de novo com toques rápidos e parciais.
 *
 * Também dispara ao rolar a lista de ícones dentro do drawer já aberto,
 * na mesma lógica de mudança de direção (rolar para cima vs para baixo).
 * Os dois gestos (abrir/fechar o drawer vs rolar a lista dentro dele) têm
 * estados de direção SEPARADOS — misturar os dois faria um gesto "fechar
 * drawer" ser ignorado por já estar na mesma direção que um scroll
 * anterior da lista, apesar de serem interações visualmente diferentes.
 *
 * Dispara diretamente nas child views VISÍVEIS NA TELA no momento da
 * inversão, em vez de depender de onBindViewHolder (que só roda quando o
 * RecyclerView recicla uma view — nem sempre coincide com "a view está
 * visível agora").
 */
package com.xaulinxs.customizations.cinematic

import android.view.View
import android.view.ViewGroup
import com.android.launcher3.BubbleTextView

object AllAppsCascadeTrigger {

    private const val DIRECTION_NONE = 0
    private const val DIRECTION_POSITIVE = 1
    private const val DIRECTION_NEGATIVE = -1

    // Estado separado para o gesto de abrir/fechar o drawer inteiro.
    @Volatile
    private var lastOpenCloseDirection = DIRECTION_NONE

    // Estado separado para o scroll da lista de ícones já aberta.
    @Volatile
    private var lastScrollDirection = DIRECTION_NONE

    /**
     * Chamar a cada mudança de progresso do drawer (mesmo ponto onde
     * CinematicScrollVelocityEffect já é alimentado). previousProgress e
     * newProgress em [0,1] (0 = aberto, 1 = fechado, convenção do
     * AllAppsTransitionController). Dispara a cascata nos ícones
     * visíveis dentro de `container` sempre que a direção muda —
     * incluindo no meio do caminho.
     */
    @JvmStatic
    fun onProgressChanged(previousProgress: Float, newProgress: Float, container: ViewGroup) {
        if (previousProgress == newProgress) return

        val direction = if (newProgress < previousProgress) DIRECTION_POSITIVE else DIRECTION_NEGATIVE

        if (direction != lastOpenCloseDirection) {
            lastOpenCloseDirection = direction
            triggerOnVisibleIcons(container)
        }
    }

    /**
     * Chamar a cada onScrolled(dx, dy) da lista de ícones do app drawer
     * já aberto. dy > 0 = rolando para baixo, dy < 0 = rolando para cima.
     * Dispara a cascata nos ícones visíveis dentro de `container` sempre
     * que a direção do scroll muda.
     */
    @JvmStatic
    fun onScrollDirectionChanged(dy: Int, container: ViewGroup) {
        if (dy == 0) return

        val direction = if (dy > 0) DIRECTION_POSITIVE else DIRECTION_NEGATIVE

        if (direction != lastScrollDirection) {
            lastScrollDirection = direction
            triggerOnVisibleIcons(container)
        }
    }

    /** Reseta a direção conhecida de abrir/fechar e de scroll — chamar quando cada gesto termina de assentar. */
    @JvmStatic
    fun reset() {
        lastOpenCloseDirection = DIRECTION_NONE
        lastScrollDirection = DIRECTION_NONE
    }

    private fun triggerOnVisibleIcons(container: ViewGroup) {
        val icons = ArrayList<View>()
        collectVisibleBubbleTextViews(container, icons)
        icons.forEachIndexed { index, icon ->
            AllAppsIconEnterEffect.animateEnter(icon, index)
        }
    }

    private fun collectVisibleBubbleTextViews(view: View, out: MutableList<View>) {
        if (view is BubbleTextView && view.visibility == View.VISIBLE) {
            out.add(view)
            return
        }
        if (view is ViewGroup) {
            for (i in 0 until view.childCount) {
                collectVisibleBubbleTextViews(view.getChildAt(i), out)
            }
        }
    }
}
