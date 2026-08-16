/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Leva o efeito de cascata giratória 720° (AllAppsIconEnterEffect, já usado
 * no app drawer e no widget picker) para o Workspace: ícones E widgets
 * das páginas do launcher também giram em cascata ao rolar entre telas.
 *
 * ATUALIZAÇÃO (pedido do usuário): a versão anterior disparava a cada
 * MUDANÇA DE DIREÇÃO durante o próprio arrasto (igual ao AllApps). Isso
 * ofuscava o efeito de coverflow 3D (CinematicCoverFlowEffect) — a
 * cascata demora pra "cair" (física suavizada do item 1: stiffness 15f,
 * stagger 110ms) e competia visualmente com a rotação 3D das páginas
 * enquanto elas ainda estavam se movendo. Agora o disparo é ADIADO: só
 * acontece quando o scroll ASSENTA de vez (mesmo ponto de
 * onScrollSettled/reset já usado pelo blur de velocidade), e só se de
 * fato houve movimento de página desde o último assentamento — não mais
 * durante o arrasto. Isso libera o coverflow para ser visto sem
 * concorrência, e a cascata vira um "acabamento" depois que a página já
 * está parada.
 *
 * Diferença de arquitetura em relação ao AllApps: lá, os ícones "surgem"
 * de verdade (drawer abrindo, RecyclerView populando) e a cascata reage
 * ao próprio gesto em tempo real. No Workspace as páginas vizinhas já
 * ficam sempre montadas por baixo do pano — não há um momento nativo de
 * "entrada", e agora nem reage mais ao gesto em si. Por isso a cascata
 * aqui dispara sobre as views JÁ EXISTENTES, sem tocar em nenhuma lógica
 * de posicionamento, e só depois que o movimento parou.
 *
 * Escopo por página (confirmado com o usuário, mantido na atualização
 * acima): quando dispara, a cascata roda em TODAS as páginas visíveis na
 * tela naquele momento — a página que ficou central E a(s) que ainda
 * está(ão) entrando/saindo pela lateral — não só a página central.
 *
 * Widgets: diferente do AllApps (só BubbleTextView), aqui o container de
 * cada página (ShortcutAndWidgetContainer) mistura BubbleTextView e
 * LauncherAppWidgetHostView — os dois tipos são coletados e giram juntos.
 */
package com.xaulinxs.customizations.cinematic

import android.view.View
import android.view.ViewGroup
import com.android.launcher3.BubbleTextView
import com.android.launcher3.widget.LauncherAppWidgetHostView

object WorkspaceCascadeTrigger {

    // Não guardamos mais a direção pra disparar durante o arrasto — só
    // marcamos que houve movimento, para decidir no assentamento se vale
    // a pena disparar a cascata (evita disparar em toques que nem
    // chegaram a mover a página).
    @Volatile
    private var hasPendingMovement = false

    /**
     * Chamar a cada mudança de posição de scroll do Workspace (arrasto
     * manual ou fling — mesmos pontos já alimentando
     * CinematicScrollVelocityEffect.onScrollPositionChanged em
     * PagedView.java). Não dispara mais a cascata aqui — só registra que
     * houve movimento, para o disparo real acontecer em reset(), quando
     * o scroll assenta de vez.
     */
    @JvmStatic
    fun onScrollPositionChanged(pages: ViewGroup, newScroll: Float, previousScroll: Float) {
        if (!newScroll.isFinite() || !previousScroll.isFinite()) return
        if (newScroll == previousScroll) return
        hasPendingMovement = true
    }

    /**
     * Chamar quando o scroll assenta de vez (mesmo ponto do
     * onScrollSettled do blur de velocidade). Dispara a cascata nas
     * páginas atualmente visíveis SE houve movimento desde o último
     * assentamento — evita disparar em toques que não moveram a página.
     * `pages` é o próprio PagedView/Workspace (ViewGroup cujos filhos
     * diretos são as CellLayout/páginas).
     */
    @JvmStatic
    fun reset(pages: ViewGroup) {
        if (hasPendingMovement) {
            triggerOnVisiblePages(pages)
        }
        hasPendingMovement = false
    }

    private fun triggerOnVisiblePages(pages: ViewGroup) {
        for (i in 0 until pages.childCount) {
            val page = pages.getChildAt(i)
            // Só páginas de fato visíveis na tela agora (evita disparar em
            // páginas fora da faixa visível que o PagedView mantém
            // infladas para scroll suave, mas que o usuário não está vendo).
            if (page.visibility != View.VISIBLE || !page.getLocalVisibleRect(TEMP_RECT)) continue

            val items = ArrayList<View>()
            collectIconsAndWidgets(page, items)
            items.forEachIndexed { index, item ->
                AllAppsIconEnterEffect.animateEnter(item, index)
            }
        }
    }

    private val TEMP_RECT = android.graphics.Rect()

    private fun collectIconsAndWidgets(view: View, out: MutableList<View>) {
        if ((view is BubbleTextView || view is LauncherAppWidgetHostView) &&
            view.visibility == View.VISIBLE
        ) {
            out.add(view)
            return
        }
        if (view is ViewGroup) {
            for (i in 0 until view.childCount) {
                collectIconsAndWidgets(view.getChildAt(i), out)
            }
        }
    }
}

// XAULINXS_WORKSPACE_CASCADE_TRIGGER_FILE
