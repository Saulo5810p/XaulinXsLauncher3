#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XaulinXs Customizations — Feature 9/N: cascata giratória 720° também no
Workspace (ícones E widgets das páginas do launcher), ao rolar entre
telas — mesmo efeito já aprovado no App Drawer e no Widget Picker,
priorizado pelo usuário na frente dos demais itens da próxima fase
(PROXIMA_FASE_BLUR_DOCK_QSB.md).

Diferença de arquitetura em relação ao AllApps: lá os ícones "surgem" de
verdade (drawer abrindo, lista populando). No Workspace as páginas
vizinhas já ficam sempre montadas por baixo do pano — não existe um
momento nativo de "entrada". Decisão confirmada com o usuário: a cascata
dispara a cada MUDANÇA DE DIREÇÃO do gesto de arrastar entre páginas
(mesmo padrão já usado no AllAppsCascadeTrigger), rodando sobre as views
já existentes — sem alterar nenhuma lógica de posicionamento/scroll real.

Escopo confirmado com o usuário: dispara em TODAS as páginas visíveis na
tela no momento da inversão (a que está ficando central + a(s) que
ainda está(ão) entrando/saindo pela lateral), não só a página central.

Widgets: diferente do AllApps (só BubbleTextView), o container de cada
página do Workspace (ShortcutAndWidgetContainer) mistura BubbleTextView
e LauncherAppWidgetHostView — os dois tipos giram juntos.

Reaproveita a MESMA física já suavizada no fix_cinematic_8 (stiffness
15f, dampingRatio 0.78, stagger 110ms) via AllAppsIconEnterEffect —
nenhum valor novo de física é introduzido, garantindo a mesma sensação
"cinematográfica" aprovada pelo usuário.

Arquivo novo:
  - src/com/xaulinxs/customizations/cinematic/WorkspaceCascadeTrigger.kt

Hooks (3, todos de 1 linha, nos MESMOS pontos já usados pelo blur de
velocidade da feature 2 em PagedView.java — reaproveita a infraestrutura
de observação já validada, não cria um sensor de scroll novo):
  1) Arrasto manual do dedo (delta calculado a cada ACTION_MOVE)
  2) Fling/animação do OverScroller (computeScrollHelper)
  3) Reset da direção conhecida quando o scroll assenta de vez
     (mesmo ponto do onScrollSettled do blur de velocidade)

Todas as edições são ADITIVAS: nenhuma lógica de scroll, CellLayout ou
posicionamento é alterada — só efeito visual observacional por cima.
Script idempotente — pode rodar várias vezes sem duplicar nada.

Uso:
    python3 feature_cinematic_9_workspace_cascade.py /caminho/do/repo
    (ou rode de dentro da raiz do repo sem argumento)
"""

import os
import sys

MARKER_DRAG_HOOK = "// XAULINXS_WORKSPACE_CASCADE_HOOK_DRAG"
MARKER_FLING_HOOK = "// XAULINXS_WORKSPACE_CASCADE_HOOK_FLING"
MARKER_RESET_HOOK = "// XAULINXS_WORKSPACE_CASCADE_HOOK_RESET"
MARKER_NEW_FILE = "// XAULINXS_WORKSPACE_CASCADE_TRIGGER_FILE"

NEW_FILE_PATH = "src/com/xaulinxs/customizations/cinematic/WorkspaceCascadeTrigger.kt"
PAGEDVIEW_REL_PATH = "src/com/android/launcher3/PagedView.java"

NEW_FILE_CONTENT = '''/*
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

''' + f"{MARKER_NEW_FILE}\n"


def find_repo_root(start):
    candidates = [start] + ([os.path.join(start, d) for d in os.listdir(start)] if os.path.isdir(start) else [])
    for c in candidates:
        if os.path.isfile(os.path.join(c, PAGEDVIEW_REL_PATH)):
            return c
    return None


def write_new_file(repo_root):
    path = os.path.join(repo_root, NEW_FILE_PATH)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read()
        if MARKER_NEW_FILE in existing:
            print(f"[=] {NEW_FILE_PATH} já existe e está atualizado — pulando.")
            return
        print(f"[~] {NEW_FILE_PATH} existe mas parece desatualizado — sobrescrevendo.")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(NEW_FILE_CONTENT)
    print(f"[+] Criado {NEW_FILE_PATH}")


def patch_pagedview(repo_root):
    path = os.path.join(repo_root, PAGEDVIEW_REL_PATH)
    if not os.path.isfile(path):
        print(f"[!] ERRO: {path} não encontrado. Estrutura do repo mudou? Abortando estes hooks.")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if MARKER_DRAG_HOOK in content and MARKER_FLING_HOOK in content and MARKER_RESET_HOOK in content:
        print("[=] PagedView.java já tem os 3 hooks da cascata do Workspace — pulando.")
        return True

    changed = False

    # --- Hook 1: arrasto manual (mesmo ponto do CinematicScrollVelocityEffect no delta) ---
    if MARKER_DRAG_HOOK not in content:
        old_drag = (
            "                if (delta != 0) {\n"
            "                    mOrientationHandler.setPrimary(this, VIEW_SCROLL_BY, delta);\n"
            "                    // XaulinXs Customizations: motion blur + aberração\n"
            "                    // cromática também durante o arrasto manual (dedo ainda\n"
            "                    // na tela, antes de qualquer fling do OverScroller).\n"
            "                    // Puramente observacional, roda depois do scroll real.\n"
            "                    com.xaulinxs.customizations.cinematic.CinematicScrollVelocityEffect\n"
            "                            .onScrollPositionChanged(this,\n"
            "                                    (float) mOrientationHandler.getPrimaryScroll(this));\n"
        )
        if old_drag not in content:
            print("[!] ERRO: âncora do hook de arrasto (delta) não encontrada em PagedView.java — abortando.")
            return False
        if content.count(old_drag) > 1:
            print("[!] ERRO: âncora do hook de arrasto aparece mais de uma vez — abortando por segurança.")
            return False
        new_drag = old_drag + (
            "                    // XaulinXs Customizations: cascata giratória 720° nos\n"
            "                    // ícones/widgets das páginas visíveis, ao mudar a direção\n"
            "                    // do arrasto manual. Mesmo padrão do AllAppsCascadeTrigger.\n"
            "                    " + MARKER_DRAG_HOOK + "\n"
            "                    com.xaulinxs.customizations.cinematic.WorkspaceCascadeTrigger\n"
            "                            .onScrollPositionChanged(this,\n"
            "                                    (float) mOrientationHandler.getPrimaryScroll(this),\n"
            "                                    (float) mOrientationHandler.getPrimaryScroll(this) - delta);\n"
        )
        content = content.replace(old_drag, new_drag, 1)
        changed = True
        print("[+] Hook de arrasto manual (cascata Workspace) aplicado.")

    # --- Hook 2: fling (mesmo ponto do CinematicScrollVelocityEffect no computeScrollHelper) ---
    if MARKER_FLING_HOOK not in content:
        old_fling = (
            "            invalidate();\n"
            "            // XaulinXs Customizations: motion blur + aberração cromática\n"
            "            // proporcional à velocidade do fling entre páginas, portado do\n"
            "            // RetroPlayer. Puramente observacional — não altera newPos nem\n"
            "            // qualquer lógica de scroll real acima.\n"
            "            com.xaulinxs.customizations.cinematic.CinematicScrollVelocityEffect\n"
            "                    .onScrollPositionChanged(this, (float) newPos);\n"
            "            return true;\n"
        )
        if old_fling not in content:
            print("[!] ERRO: âncora do hook de fling não encontrada em PagedView.java — abortando.")
            return False
        if content.count(old_fling) > 1:
            print("[!] ERRO: âncora do hook de fling aparece mais de uma vez — abortando por segurança.")
            return False
        new_fling = old_fling.replace(
            "            return true;\n",
            "            // XaulinXs Customizations: cascata giratória 720° nos\n"
            "            // ícones/widgets das páginas visíveis, ao mudar a direção do fling.\n"
            "            " + MARKER_FLING_HOOK + "\n"
            "            com.xaulinxs.customizations.cinematic.WorkspaceCascadeTrigger\n"
            "                    .onScrollPositionChanged(this, (float) newPos, (float) oldPos);\n"
            "            return true;\n"
        )
        content = content.replace(old_fling, new_fling, 1)
        changed = True
        print("[+] Hook de fling (cascata Workspace) aplicado.")

    # --- Hook 3: reset ao assentar (mesmo ponto do onScrollSettled do blur de velocidade) ---
    if MARKER_RESET_HOOK not in content:
        old_settle = (
            "        // XaulinXs Customizations: scroll/fling parou de vez (nenhum dos\n"
            "        // dois ramos acima segue em andamento) — zera o efeito cinematográfico.\n"
            "        com.xaulinxs.customizations.cinematic.CinematicScrollVelocityEffect\n"
            "                .onScrollSettled(this);\n"
            "        return false;\n"
        )
        if old_settle not in content:
            print("[!] ERRO: âncora do hook de reset não encontrada em PagedView.java — abortando.")
            return False
        if content.count(old_settle) > 1:
            print("[!] ERRO: âncora do hook de reset aparece mais de uma vez — abortando por segurança.")
            return False
        new_settle = old_settle.replace(
            "        return false;\n",
            "        // XaulinXs Customizations: reseta a direção conhecida da cascata\n"
            "        // do Workspace junto com o reset do blur de velocidade.\n"
            "        " + MARKER_RESET_HOOK + "\n"
            "        com.xaulinxs.customizations.cinematic.WorkspaceCascadeTrigger.reset();\n"
            "        return false;\n"
        )
        content = content.replace(old_settle, new_settle, 1)
        changed = True
        print("[+] Hook de reset (cascata Workspace) aplicado.")

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return True


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else "."
    repo_root = find_repo_root(os.path.abspath(start))
    if repo_root is None:
        print(f"[!] ERRO: não encontrei {PAGEDVIEW_REL_PATH} a partir de '{start}'. "
              f"Rode este script de dentro da raiz do repo, ou passe o caminho como argumento.")
        sys.exit(1)

    print(f"Repo detectado em: {repo_root}\n")

    write_new_file(repo_root)
    ok = patch_pagedview(repo_root)

    print()
    if ok:
        print("Concluído. Rode ./gradlew assembleDebug para compilar.")
    else:
        print("Concluído com erros — revise as mensagens [!] acima antes de compilar.")
        sys.exit(1)


if __name__ == "__main__":
    main()
