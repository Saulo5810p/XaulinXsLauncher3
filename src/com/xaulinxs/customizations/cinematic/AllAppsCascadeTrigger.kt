/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * ATUALIZAÇÃO (pedido do usuário): a versão anterior disparava a cascata
 * SEQUENCIAL (um ícone de cada vez, com stagger de posição) só na
 * MUDANÇA DE DIREÇÃO do gesto. Isso criava um delay perceptível entre o
 * primeiro e o último ícone, e só reiniciava a cascata quando o dedo
 * invertia de sentido. Agora o comportamento é: TODOS os ícones visíveis
 * giram JUNTOS (sem stagger — positionInGrid sempre 0), e a animação é
 * DISPARADA DE NOVO A CADA EVENTO DE MOVIMENTO (todo onScrolled/todo
 * onProgressChanged), não só na mudança de direção — criando uma
 * "cascata infinita" enquanto o dedo desliza, pra cima ou pra baixo,
 * tanto rolando a lista já aberta quanto abrindo/fechando o drawer
 * inteiro. AllAppsIconEnterEffect.animateEnter cancela a spring anterior
 * de cada ícone antes de reiniciar (ver runSpring), evitando springs
 * acumuladas/conflitantes ao reiniciar em todo frame.
 *
 * Efeito reservado ao APP DRAWER apenas — Widget Picker mantém o
 * comportamento sequencial/stagger anterior de propósito (o usuário
 * achou o resultado "perfeito" lá, mais devagar item a item), e o
 * Workspace tem lógica própria e SEPARADA (WorkspaceCascadeTrigger,
 * disparo adiado até o scroll assentar, para não ofuscar o coverflow 3D).
 *
 * Dispara diretamente nas child views VISÍVEIS NA TELA a cada evento, em
 * vez de depender de onBindViewHolder (que só roda quando o RecyclerView
 * recicla uma view — nem sempre coincide com "a view está visível agora").
 */
package com.xaulinxs.customizations.cinematic

import android.view.View
import android.view.ViewGroup
import com.android.launcher3.BubbleTextView

object AllAppsCascadeTrigger {

    /**
     * Chamar a cada mudança de progresso do drawer (mesmo ponto onde
     * CinematicScrollVelocityEffect já é alimentado). Dispara a cascata
     * SEM STAGGER (todos os ícones visíveis juntos) em TODO evento de
     * movimento — não só na mudança de direção — enquanto o drawer está
     * de fato se movendo (abrindo ou fechando).
     */
    @JvmStatic
    fun onProgressChanged(previousProgress: Float, newProgress: Float, container: ViewGroup) {
        if (previousProgress == newProgress) return
        triggerOnVisibleIcons(container)
    }

    /**
     * Chamar a cada onScrolled(dx, dy) da lista de ícones do app drawer
     * já aberto. Dispara a cascata SEM STAGGER (todos os ícones visíveis
     * juntos) em TODO evento de scroll (dy != 0) — pra cima ou pra baixo
     * — não só na mudança de direção.
     */
    @JvmStatic
    fun onScrollDirectionChanged(dy: Int, container: ViewGroup) {
        if (dy == 0) return
        triggerOnVisibleIcons(container)
    }

    /**
     * Mantido por compatibilidade com os pontos de chamada existentes
     * (AllAppsRecyclerView, AllAppsTransitionController chamam reset() ao
     * assentar) — não há mais estado de direção pra zerar, mas a função
     * continua existindo pra não quebrar essas chamadas.
     */
    @JvmStatic
    fun reset() {
        // Sem estado a resetar — a cascata contínua não guarda direção.
    }

    private fun triggerOnVisibleIcons(container: ViewGroup) {
        val icons = ArrayList<View>()
        collectVisibleBubbleTextViews(container, icons)
        // positionInGrid = 0 pra todos: remove o stagger, todos giram
        // juntos (delayMs = 0, modo contínuo explícito — ver
        // AllAppsIconEnterEffect.animateEnter).
        icons.forEach { icon ->
            AllAppsIconEnterEffect.animateEnter(icon, 0, continuous = true)
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
