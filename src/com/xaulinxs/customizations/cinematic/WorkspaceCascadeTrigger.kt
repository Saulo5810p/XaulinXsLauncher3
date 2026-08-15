/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Leva o efeito de cascata giratória 720° (AllAppsIconEnterEffect, já usado
 * no app drawer e no widget picker) para o Workspace: ícones E widgets
 * das páginas do launcher também giram em cascata ao rolar entre telas.
 *
 * Mesma lógica de detecção de MUDANÇA DE DIREÇÃO do AllAppsCascadeTrigger
 * (dispara toda vez que o gesto de arrastar entre páginas inverte de
 * sentido, inclusive no meio do caminho) — decisão do usuário de manter
 * o comportamento idêntico ao já aprovado no app drawer.
 *
 * Diferença de arquitetura em relação ao AllApps: lá, os ícones "surgem"
 * de verdade (drawer abrindo, RecyclerView populando). No Workspace as
 * páginas vizinhas já ficam sempre montadas por baixo do pano — não há um
 * momento nativo de "entrada". Por isso a cascata aqui dispara sobre as
 * views JÁ EXISTENTES, sem tocar em nenhuma lógica de posicionamento.
 *
 * Escopo por página (confirmado com o usuário): ao inverter a direção,
 * a cascata roda em TODAS as páginas visíveis na tela naquele momento —
 * a página que está ficando central E a(s) que ainda está(ão)
 * entrando/saindo pela lateral — não só a página central.
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

    private const val DIRECTION_NONE = 0
    private const val DIRECTION_POSITIVE = 1
    private const val DIRECTION_NEGATIVE = -1

    @Volatile
    private var lastDirection = DIRECTION_NONE

    /**
     * Chamar a cada mudança de posição de scroll do Workspace (arrasto
     * manual ou fling — mesmos pontos já alimentando
     * CinematicScrollVelocityEffect.onScrollPositionChanged em
     * PagedView.java). newScroll é a posição de scroll bruta (px);
     * comparamos com a última chamada para saber a direção instantânea.
     * `pages` é o próprio PagedView/Workspace (ViewGroup cujos filhos
     * diretos são as CellLayout/páginas).
     */
    @JvmStatic
    fun onScrollPositionChanged(pages: ViewGroup, newScroll: Float, previousScroll: Float) {
        if (!newScroll.isFinite() || !previousScroll.isFinite()) return
        val delta = newScroll - previousScroll
        if (delta == 0f) return

        val direction = if (delta > 0) DIRECTION_POSITIVE else DIRECTION_NEGATIVE

        if (direction != lastDirection) {
            lastDirection = direction
            triggerOnVisiblePages(pages)
        }
    }

    /** Reseta a direção conhecida — chamar quando o scroll assenta de vez (mesmo ponto do onScrollSettled do blur de velocidade). */
    @JvmStatic
    fun reset() {
        lastDirection = DIRECTION_NONE
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
