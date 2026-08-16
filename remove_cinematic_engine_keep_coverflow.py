#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XaulinXs Customizations — REMOCAO EM MASSA do motor cinematografico.

Motivo (relato do usuario): testando em resolucao real do aparelho (nao a
216p usada durante o desenvolvimento), rolar o Workspace sem parar travou
o Android por completo (apps fechados, celular parou de responder). Risco
grave demais para manter.

O QUE FICA:
  - Tudo que existia no Launcher3 ANTES de qualquer efeito cinematografico
    (comportamento nativo AOSP).
  - Feature 7: coverflow 3D verdadeiro por pagina no Workspace
    (CinematicCoverFlowEffect.kt) + tilt por giroscopio (GyroTiltProvider.kt).
    Usuario confirmou que isso e leve e nao tem relacao com o problema de
    travamento — roda sozinho, sem blur/RenderEffect pesado.

O QUE SAI (tudo mais):
  - Feature 1: giro/blur/escala ao tocar icones (CinematicPressEffects.kt)
  - Feature 2: motion blur + aberracao cromatica no scroll (velocidade)
    (CinematicScrollVelocityEffect.kt) — INCLUSIVE a parte que rodava
    junto com o coverflow no Workspace (hook removido de
    Workspace/PagedView, coverflow fica sozinho)
  - Features 3/4: cascata giratoria 720 graus no App Drawer e Widget
    Picker (AllAppsCascadeTrigger.kt, AllAppsIconEnterEffect.kt,
    CinematicWidgetSheetEffects.kt)
  - Feature 5: blur/tilt 3D ao arrastar icones (CinematicDragEffect.kt)
  - Feature 6: blur ao redimensionar widgets (CinematicResizeEffect.kt)
  - Features 9/11: cascata giratoria no Workspace
    (WorkspaceCascadeTrigger.kt)
  - Feature 10: blur pesado por posicao no Workspace
    (WorkspaceDepthBlurEffect.kt)
  - CinematicShader.kt (motor AGSL usado só pelas features acima, nao
    usado pelo coverflow que fica)

Arquivos REMOVIDOS por completo (9 de 12 no pacote cinematic/):
  - CinematicPressEffects.kt
  - CinematicScrollVelocityEffect.kt
  - CinematicShader.kt
  - AllAppsCascadeTrigger.kt
  - AllAppsIconEnterEffect.kt
  - CinematicWidgetSheetEffects.kt
  - CinematicDragEffect.kt
  - CinematicResizeEffect.kt
  - WorkspaceCascadeTrigger.kt
  - WorkspaceDepthBlurEffect.kt

Arquivos MANTIDOS no pacote cinematic/ (2):
  - CinematicCoverFlowEffect.kt
  - GyroTiltProvider.kt

Arquivos AOSP com hooks REVERTIDOS (remove só as linhas do motor
cinematografico, mantendo o resto 100% intacto):
  - BubbleTextView.java (feature 1)
  - Launcher.java (feature 11 — hook do widget adicionado)
  - PagedView.java (features 2/9/11 — TODOS os hooks saem, nada do
    coverflow mora aqui)
  - Workspace.java (feature 10 — remove SO o hook do blur pesado,
    MANTEM o hook do coverflow 3D/feature 7 intocado — edicao cirurgica)
  - allapps/AllAppsRecyclerView.java (features 2/3)
  - allapps/AllAppsTransitionController.java (features 2/3)
  - dragndrop/DragLayer.java (feature 5)
  - dragndrop/DragView.java (feature 5)
  - AppWidgetResizeFrame.kt (feature 6)
  - modules/widgetpicker/.../WidgetsGrid.kt (feature 3/4 no Compose)
  - modules/widgetpicker/.../TitledBottomSheet.kt (feature 3/4 no
    Compose — remove o CompositionLocalProvider por completo,
    "desenrolando" o bloco interno que ele envolvia)

Idempotente: cada remocao checa se o marcador/import/arquivo ainda existe
antes de agir — pode rodar varias vezes sem erro, mesmo em cima de um
repo ja parcialmente revertido.

Uso:
    python3 remove_cinematic_engine_keep_coverflow.py /caminho/do/repo
    (ou rode de dentro da raiz do repo sem argumento)
"""

import os
import sys

CINEMATIC_DIR = "src/com/xaulinxs/customizations/cinematic"

FILES_TO_REMOVE = [
    f"{CINEMATIC_DIR}/CinematicPressEffects.kt",
    f"{CINEMATIC_DIR}/CinematicScrollVelocityEffect.kt",
    f"{CINEMATIC_DIR}/CinematicShader.kt",
    f"{CINEMATIC_DIR}/AllAppsCascadeTrigger.kt",
    f"{CINEMATIC_DIR}/AllAppsIconEnterEffect.kt",
    f"{CINEMATIC_DIR}/CinematicWidgetSheetEffects.kt",
    f"{CINEMATIC_DIR}/CinematicDragEffect.kt",
    f"{CINEMATIC_DIR}/CinematicResizeEffect.kt",
    f"{CINEMATIC_DIR}/WorkspaceCascadeTrigger.kt",
    f"{CINEMATIC_DIR}/WorkspaceDepthBlurEffect.kt",
]

FILES_TO_KEEP = [
    f"{CINEMATIC_DIR}/CinematicCoverFlowEffect.kt",
    f"{CINEMATIC_DIR}/GyroTiltProvider.kt",
]

PAGEDVIEW_REL_PATH = "src/com/android/launcher3/PagedView.java"


def find_repo_root(start):
    candidates = [start] + ([os.path.join(start, d) for d in os.listdir(start)] if os.path.isdir(start) else [])
    for c in candidates:
        if os.path.isfile(os.path.join(c, PAGEDVIEW_REL_PATH)):
            return c
    return None


def remove_files(repo_root):
    removed = 0
    already_gone = 0
    for rel_path in FILES_TO_REMOVE:
        path = os.path.join(repo_root, rel_path)
        if os.path.isfile(path):
            os.remove(path)
            print(f"[-] Removido: {rel_path}")
            removed += 1
        else:
            already_gone += 1
    print(f"    ({removed} removido(s), {already_gone} já não existia(m))")

    for rel_path in FILES_TO_KEEP:
        path = os.path.join(repo_root, rel_path)
        if os.path.isfile(path):
            print(f"[=] Mantido (coverflow/giroscópio): {rel_path}")
        else:
            print(f"[!] AVISO: {rel_path} não encontrado — deveria ter sido mantido, mas já não existe.")


def revert_block(path, old_block, label, required=True):
    """Remove old_block de path, se presente. Idempotente: se old_block
    não está presente, assume que já foi revertido (ou nunca existiu) e
    não faz nada — a menos que required=True e o arquivo nem tenha uma
    versão "já revertida" detectável, nesse caso avisa."""
    if not os.path.isfile(path):
        print(f"[!] ERRO: arquivo não encontrado para reverter '{label}': {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if old_block not in content:
        return content  # já revertido ou nunca existiu — idempotente
    if content.count(old_block) > 1:
        print(f"[!] ERRO: bloco de '{label}' aparece mais de uma vez em {path} — abortando por segurança, revise manualmente.")
        return False
    content = content.replace(old_block, "", 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[-] Revertido: {label} ({os.path.basename(path)})")
    return content


def revert_bubbletextview(repo_root):
    path = os.path.join(repo_root, "src/com/android/launcher3/BubbleTextView.java")
    old = (
        "        // XaulinXs Customizations: efeito visual de giro/blur/escala,\n"
        "        // puramente observacional — não altera o retorno nem consome\n"
        "        // o evento. O clique/long-press original continua 100% intacto.\n"
        "        com.xaulinxs.customizations.cinematic.CinematicPressEffects.onTouchObserved(this, event);\n"
    )
    revert_block(path, old, "toque em ícone (feature 1)")


def revert_launcher(repo_root):
    path = os.path.join(repo_root, "src/com/android/launcher3/Launcher.java")
    old = (
        "            // XaulinXs Customizations: efeito leve de entrada (giro 720°\n"
        "            // + escala + fade, mesmo AllAppsIconEnterEffect usado nos\n"
        "            // ícones do app drawer) no widget recém-adicionado à\n"
        "            // Workspace — pedido do usuário, dispara uma única vez.\n"
        "            // continuous NÃO é passado (fica no default false) — isso é\n"
        "            // um giro individual normal, não o modo contínuo do App\n"
        "            // Drawer (que só ativa quando explicitamente pedido via\n"
        "            // AllAppsCascadeTrigger).\n"
        "            // XAULINXS_WIDGET_ADD_ENTER_HOOK\n"
        "            com.xaulinxs.customizations.cinematic.AllAppsIconEnterEffect\n"
        "                    .animateEnter(hostView, 0);\n"
    )
    revert_block(path, old, "entrada do widget adicionado (feature 11)")


def revert_pagedview(repo_root):
    path = os.path.join(repo_root, PAGEDVIEW_REL_PATH)

    old_fling = (
        "            // XaulinXs Customizations: motion blur + aberração cromática\n"
        "            // proporcional à velocidade do fling entre páginas, portado do\n"
        "            // RetroPlayer. Puramente observacional — não altera newPos nem\n"
        "            // qualquer lógica de scroll real acima.\n"
        "            com.xaulinxs.customizations.cinematic.CinematicScrollVelocityEffect\n"
        "                    .onScrollPositionChanged(this, (float) newPos);\n"
        "            // XaulinXs Customizations: cascata giratória 720° nos\n"
        "            // ícones/widgets das páginas visíveis, ao mudar a direção do fling.\n"
        "            // XAULINXS_WORKSPACE_CASCADE_HOOK_FLING\n"
        "            com.xaulinxs.customizations.cinematic.WorkspaceCascadeTrigger\n"
        "                    .onScrollPositionChanged(this, (float) newPos, (float) oldPos);\n"
    )
    revert_block(path, old_fling, "blur+cascata no fling (features 2/9)")

    old_settle = (
        "        // XaulinXs Customizations: scroll/fling parou de vez (nenhum dos\n"
        "        // dois ramos acima segue em andamento) — zera o efeito cinematográfico.\n"
        "        com.xaulinxs.customizations.cinematic.CinematicScrollVelocityEffect\n"
        "                .onScrollSettled(this);\n"
        "        // XaulinXs Customizations: scroll assentou de vez — dispara a\n"
        "        // cascata do Workspace AGORA (adiada até aqui, pedido do\n"
        "        // usuário) se houve movimento, e zera o estado.\n"
        "        // XAULINXS_WORKSPACE_CASCADE_HOOK_RESET\n"
        "        com.xaulinxs.customizations.cinematic.WorkspaceCascadeTrigger.reset(this);\n"
    )
    revert_block(path, old_settle, "reset de blur+cascata (features 2/11)")

    old_drag = (
        "                    // XaulinXs Customizations: motion blur + aberração\n"
        "                    // cromática também durante o arrasto manual (dedo ainda\n"
        "                    // na tela, antes de qualquer fling do OverScroller).\n"
        "                    // Puramente observacional, roda depois do scroll real.\n"
        "                    com.xaulinxs.customizations.cinematic.CinematicScrollVelocityEffect\n"
        "                            .onScrollPositionChanged(this,\n"
        "                                    (float) mOrientationHandler.getPrimaryScroll(this));\n"
        "                    // XaulinXs Customizations: cascata giratória 720° nos\n"
        "                    // ícones/widgets das páginas visíveis, ao mudar a direção\n"
        "                    // do arrasto manual. Mesmo padrão do AllAppsCascadeTrigger.\n"
        "                    // XAULINXS_WORKSPACE_CASCADE_HOOK_DRAG\n"
        "                    com.xaulinxs.customizations.cinematic.WorkspaceCascadeTrigger\n"
        "                            .onScrollPositionChanged(this,\n"
        "                                    (float) mOrientationHandler.getPrimaryScroll(this),\n"
        "                                    (float) mOrientationHandler.getPrimaryScroll(this) - delta);\n"
    )
    revert_block(path, old_drag, "blur+cascata no arrasto manual (features 2/9)")


def revert_workspace(repo_root):
    """Edição CIRÚRGICA: remove SÓ o hook do blur pesado (feature 10),
    mantém o hook do coverflow 3D (feature 7) intocado."""
    path = os.path.join(repo_root, "src/com/android/launcher3/Workspace.java")
    old = (
        "                // XAULINXS_CASCADE_HOOK_DEPTH_BLUR_WORKSPACE\n"
        "                com.xaulinxs.customizations.cinematic.WorkspaceDepthBlurEffect\n"
        "                        .applyToPage(child, scrollProgress);\n"
    )
    revert_block(path, old, "blur pesado por posição (feature 10) — coverflow mantido")


def revert_allapps_recyclerview(repo_root):
    path = os.path.join(repo_root, "src/com/android/launcher3/allapps/AllAppsRecyclerView.java")

    old_idle = (
        "                // XaulinXs Customizations: scroll da lista de ícones parou\n"
        "                // — zera o motion blur/aberração cromática e a direção\n"
        "                // conhecida da cascata.\n"
        "                com.xaulinxs.customizations.cinematic.CinematicScrollVelocityEffect\n"
        "                        .onScrollSettled(this);\n"
        "                com.xaulinxs.customizations.cinematic.AllAppsCascadeTrigger.reset();\n"
    )
    revert_block(path, old_idle, "reset de blur+cascata no drawer (features 2/3)")

    old_scrolled = (
        "        // XaulinXs Customizations: motion blur + aberração cromática ao\n"
        "        // rolar a lista de ícones do app drawer, mesmo motor já usado no\n"
        "        // scroll de páginas do Workspace (feature 2) — reaproveitado sem\n"
        "        // mudanças. Usa um acumulador PRÓPRIO (não mCumulativeVerticalScroll,\n"
        "        // que o AOSP reseta a cada novo toque — resetar quebraria a\n"
        "        // suavização de velocidade do motor cinematográfico). Puramente\n"
        "        // observacional, roda depois do scroll real.\n"
        "        mXaulinXsScrollAccumulator += dy;\n"
        "        com.xaulinxs.customizations.cinematic.CinematicScrollVelocityEffect\n"
        "                .onScrollPositionChanged(this, (float) mXaulinXsScrollAccumulator);\n"
        "        // XaulinXs Customizations: giro 720° em cascata também ao rolar\n"
        "        // (não só ao abrir/fechar o drawer inteiro) — dispara nos ícones\n"
        "        // atualmente visíveis quando a direção do scroll muda (para cima\n"
        "        // vs para baixo), mesma lógica de detecção de direção usada na\n"
        "        // abertura/fechamento.\n"
        "        com.xaulinxs.customizations.cinematic.AllAppsCascadeTrigger\n"
        "                .onScrollDirectionChanged(dy, this);\n"
    )
    revert_block(path, old_scrolled, "blur+cascata no scroll do drawer (features 2/3)")

    old_accumulator = (
        "\n"
        "    // XaulinXs Customizations: acumulador de posição independente, ver\n"
        "    // comentário em onScrolled acima.\n"
        "    private int mXaulinXsScrollAccumulator = 0;\n"
    )
    revert_block(path, old_accumulator, "declaração do acumulador (feature 2)")


def revert_allapps_transition_controller(repo_root):
    path = os.path.join(repo_root, "src/com/android/launcher3/allapps/AllAppsTransitionController.java")

    old_previous_progress = "        float previousProgress = mProgress;\n"
    revert_block(path, old_previous_progress, "declaração de previousProgress (feature 3)")

    old_block = (
        "\n"
        "        // XaulinXs Customizations: motion blur + aberração cromática\n"
        "        // reagindo à velocidade da transição de abertura/fechamento do app\n"
        "        // drawer, portado do RetroPlayer. progress*shiftRange já é uma\n"
        "        // posição em pixels equivalente à do scroll de páginas — mesmo\n"
        "        // motor (CinematicScrollVelocityEffect) reaproveitado sem mudanças.\n"
        "        // Puramente observacional, roda depois da translação real acima.\n"
        "        if (mAppsView != null) {\n"
        "            com.xaulinxs.customizations.cinematic.CinematicScrollVelocityEffect\n"
        "                    .onScrollPositionChanged(mAppsView, mProgress * shiftRange);\n"
        "            if (mProgress <= 0f || mProgress >= 1f) {\n"
        "                com.xaulinxs.customizations.cinematic.CinematicScrollVelocityEffect\n"
        "                        .onScrollSettled(mAppsView);\n"
        "            }\n"
        "        }\n"
        "        // XaulinXs Customizations: dispara o giro 720° em cascata sempre\n"
        "        // que a DIREÇÃO do gesto de abrir/fechar o drawer muda — mesmo no\n"
        "        // meio do caminho, não só ao cruzar totalmente aberto/fechado.\n"
        "        // Substitui a versão anterior (janela de tempo única), que quase\n"
        "        // nunca disparava com toques rápidos e parciais.\n"
        "        if (mAppsView != null) {\n"
        "            com.xaulinxs.customizations.cinematic.AllAppsCascadeTrigger\n"
        "                    .onProgressChanged(previousProgress, mProgress, mAppsView);\n"
        "            if (mProgress <= 0f || mProgress >= 1f) {\n"
        "                com.xaulinxs.customizations.cinematic.AllAppsCascadeTrigger.reset();\n"
        "            }\n"
        "        }\n"
    )
    revert_block(path, old_block, "blur+cascata na transição do drawer (features 2/3)")


def revert_dragndrop(repo_root):
    layer_path = os.path.join(repo_root, "src/com/android/launcher3/dragndrop/DragLayer.java")
    revert_block(layer_path, "import com.xaulinxs.customizations.cinematic.CinematicDragEffect;\n",
                 "import CinematicDragEffect (feature 5)")
    old_bounce = (
        "        // XAULINXS_CASCADE_HOOK_DRAG_DROP_BOUNCE\n"
        "        mDropAnim.addListener(forEndCallback(() -> CinematicDragEffect.onDragDropSettled(view)));\n"
    )
    revert_block(layer_path, old_bounce, "bounce ao soltar ícone (feature 5)")

    view_path = os.path.join(repo_root, "src/com/android/launcher3/dragndrop/DragView.java")
    revert_block(view_path, "import com.xaulinxs.customizations.cinematic.CinematicDragEffect;\n",
                 "import CinematicDragEffect (feature 5)")
    old_move = (
        "        // XAULINXS_CASCADE_HOOK_DRAG_MOVE\n"
        "        CinematicDragEffect.onDragMove(this, mLastTouchX - touchX, mLastTouchY - touchY);\n"
    )
    revert_block(view_path, old_move, "blur/tilt ao arrastar ícone (feature 5)")


def revert_widget_resize(repo_root):
    path = os.path.join(repo_root, "src/com/android/launcher3/AppWidgetResizeFrame.kt")
    revert_block(path, "import com.xaulinxs.customizations.cinematic.CinematicResizeEffect\n",
                 "import CinematicResizeEffect (feature 6)")

    old_move = (
        "        // XAULINXS_CASCADE_HOOK_WIDGET_RESIZE_MOVE\n"
        "        CinematicResizeEffect.onResizeMove(\n"
        "            frame = this,\n"
        "            deltaX = this.deltaX,\n"
        "            deltaY = this.deltaY,\n"
        "            activeHandle = when {\n"
        "                isLeftBorderActive -> dragHandles.left\n"
        "                isRightBorderActive -> dragHandles.right\n"
        "                isTopBorderActive -> dragHandles.top\n"
        "                isBottomBorderActive -> dragHandles.bottom\n"
        "                else -> null\n"
        "            },\n"
        "        )\n"
    )
    revert_block(path, old_move, "blur ao mover alça de resize (feature 6)")

    old_settle = (
        "        // XAULINXS_CASCADE_HOOK_WIDGET_RESIZE_SETTLE\n"
        "        CinematicResizeEffect.onResizeSettled(this, dragHandles.all)\n"
    )
    revert_block(path, old_settle, "reset de blur ao soltar resize (feature 6)")


def revert_widgets_grid(repo_root):
    path = os.path.join(
        repo_root,
        "modules/widgetpicker/src/com/android/launcher3/widgetpicker/ui/components/WidgetsGrid.kt",
    )
    revert_block(path, "import com.xaulinxs.customizations.cinematic.cascadeSpinEnter\n",
                 "import cascadeSpinEnter (feature 3/4 Compose)")
    revert_block(path, "                    .cascadeSpinEnter(indexInGrid = index)\n",
                 "modifier cascadeSpinEnter no grid de widgets (feature 3/4 Compose)")


def revert_titled_bottom_sheet(repo_root):
    """Edição estrutural: remove os 3 imports do motor cinematográfico e
    'desenrola' o CompositionLocalProvider que envolvia o corpo da sheet
    (remove abertura com o hook, remove só a chave de fechamento extra)."""
    path = os.path.join(
        repo_root,
        "modules/widgetpicker/src/com/android/launcher3/widgetpicker/ui/components/bottomsheet/TitledBottomSheet.kt",
    )
    if not os.path.isfile(path):
        print(f"[!] ERRO: TitledBottomSheet.kt não encontrado — abortando esta reversão.")
        return

    marker = "XAULINXS_CASCADE_HOOK_WIDGETS_SHEET"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if marker not in content:
        print("[=] TitledBottomSheet.kt já revertido (marcador ausente) — pulando.")
        return

    # 1) Remove os 3 imports
    for imp in [
        "import com.xaulinxs.customizations.cinematic.CinematicWidgetSheetScrim\n",
        "import com.xaulinxs.customizations.cinematic.LocalCinematicWidgetsCascadeTrigger\n",
        "import com.xaulinxs.customizations.cinematic.rememberWidgetsSheetCascadeTrigger\n",
    ]:
        if imp in content:
            content = content.replace(imp, "", 1)

    # 2) Remove o bloco de abertura (hook + CompositionLocalProvider(...) {)
    old_open = (
        "        // XAULINXS_CASCADE_HOOK_WIDGETS_SHEET\n"
        "        val cinematicCascadeTrigger = rememberWidgetsSheetCascadeTrigger(scrimAlpha)\n"
        "        CinematicWidgetSheetScrim(\n"
        "            scrimAlpha = scrimAlpha,\n"
        "            scrimColor = WidgetPickerTheme.colors.sheetBackgroundScrim,\n"
        "        )\n"
        "\n"
        "        CompositionLocalProvider(\n"
        "            LocalCinematicWidgetsCascadeTrigger provides cinematicCascadeTrigger\n"
        "        ) {\n"
    )
    if old_open not in content:
        print("[!] ERRO: bloco de abertura do CompositionLocalProvider não encontrado em TitledBottomSheet.kt — abortando esta reversão, revise manualmente.")
        return
    if content.count(old_open) > 1:
        print("[!] ERRO: bloco de abertura aparece mais de uma vez — abortando por segurança.")
        return
    content = content.replace(old_open, "", 1)

    # 3) Remove a chave de fechamento EXTRA do provider (a que sobrou com
    # indentação de 8 espaços logo antes do fechamento do Box externo,
    # que também é "        }\n" — por isso usamos a âncora de contexto
    # completa, com as duas linhas seguintes, para garantir que pegamos
    # a chave certa e não uma coincidência).
    old_close = (
        "            }\n"
        "        }\n"
        "        }\n"
        "    }\n"
        "}\n"
    )
    new_close = (
        "            }\n"
        "        }\n"
        "    }\n"
        "}\n"
    )
    if old_close not in content:
        print("[!] ERRO: âncora de fechamento não encontrada em TitledBottomSheet.kt após remover a abertura — abortando, revise manualmente (arquivo pode ter ficado com imports/abertura removidos mas fechamento intacto).")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return
    if content.count(old_close) > 1:
        print("[!] ERRO: âncora de fechamento aparece mais de uma vez — abortando por segurança antes de tocar no fechamento (imports/abertura já foram removidos).")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return
    content = content.replace(old_close, new_close, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[-] Revertido: CompositionLocalProvider da cascata no Widget Picker (TitledBottomSheet.kt)")


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else "."
    repo_root = find_repo_root(os.path.abspath(start))
    if repo_root is None:
        print(f"[!] ERRO: não encontrei {PAGEDVIEW_REL_PATH} a partir de '{start}'.")
        print("    Rode este script de dentro da raiz do repo, ou passe o caminho como argumento.")
        sys.exit(1)

    print(f"Repo detectado em: {repo_root}\n")

    print("=== Removendo arquivos do motor cinematográfico ===")
    remove_files(repo_root)

    print("\n=== Revertendo hooks em arquivos AOSP ===")
    revert_bubbletextview(repo_root)
    revert_launcher(repo_root)
    revert_pagedview(repo_root)
    revert_workspace(repo_root)  # cirúrgico: mantém o hook do coverflow
    revert_allapps_recyclerview(repo_root)
    revert_allapps_transition_controller(repo_root)
    revert_dragndrop(repo_root)
    revert_widget_resize(repo_root)
    revert_widgets_grid(repo_root)
    revert_titled_bottom_sheet(repo_root)

    print("\nConcluído. Rode ./gradlew assembleDebug para compilar.")
    print("Deve restar SOMENTE: comportamento nativo do Launcher3 + coverflow 3D")
    print("das páginas do Workspace (rotação em perspectiva + tilt por giroscópio).")


if __name__ == "__main__":
    main()
