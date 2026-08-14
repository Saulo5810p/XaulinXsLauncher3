"""
XaulinXs Customizations — Correcao de logica da Feature 3/N: a cascata de
giro 720 nos icones do app drawer so disparava quando o drawer saia de
quase-fechado (progress >= 0.98) para abrindo. Abrindo/fechando rapido e
repetidamente, isso quase nunca disparava de novo (o progress raramente
voltava perto de 0.98 antes do usuario tocar de novo).

NOVA LOGICA: dispara sempre que a DIRECAO do gesto muda (abrir->fechar ou
fechar->abrir), mesmo no meio do caminho, direto nos icones VISIVEIS NA
TELA naquele momento (nao mais amarrado a onBindViewHolder/reciclagem).

TAMBEM ADICIONADO (pedido explicito do usuario): o mesmo efeito de motion
blur/aberracao cromatica E giro cascata ao ROLAR a lista de icones dentro
do drawer ja aberto, nao so ao abrir/fechar o drawer inteiro.

O que este script faz:
1. Remove AllAppsEnterCascadeState.kt (logica antiga de janela de tempo,
   obsoleta)
2. Cria AllAppsCascadeTrigger.kt (logica nova de deteccao de direcao,
   com estados separados para abrir/fechar vs scroll da lista)
3. Reverte o hook antigo em AllAppsTransitionController.java e aplica o novo
4. Remove o hook antigo (agora inutil) em BaseAllAppsAdapter.java
5. Adiciona motion blur + giro cascata no scroll de AllAppsRecyclerView.java

Pre-requisito: ja ter rodado feature_cinematic_3_allapps_open_close.py e
fix_cinematic_3_rotationz.py antes.

Idempotente: pode rodar de novo sem duplicar nada.

USO (Termux, na raiz do projeto):
    python3 fix_cinematic_3b_direction_based_cascade.py
"""
from pathlib import Path

def write_if_absent(path_str, content):
    path = Path(path_str)
    if path.exists():
        print(f"SKIP (ja existe): {path_str}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"CRIADO: {path_str}")

def replace_once(path_str, old, new, label, required=True):
    path = Path(path_str)
    if not path.exists():
        print(f"SKIP ({label}): arquivo nao existe ({path_str})")
        return
    content = path.read_text(encoding="utf-8")
    if new in content:
        print(f"SKIP ({label}): ja aplicado")
        return
    if old not in content:
        msg = f"ancora nao encontrada em {path_str} ({label})"
        if required:
            raise AssertionError(msg + " — cola o arquivo atual, pode ter mudado")
        print(f"SKIP ({label}): {msg}")
        return
    assert content.count(old) == 1, f"ancora aparece {content.count(old)}x em {path_str} ({label}), precisa ser unica"
    content = content.replace(old, new)
    path.write_text(content, encoding="utf-8")
    print(f"APLICADO: {label}")

def delete_if_exists(path_str):
    path = Path(path_str)
    if path.exists():
        path.unlink()
        print(f"APAGADO: {path_str}")
    else:
        print(f"SKIP (ja nao existe): {path_str}")


# ---------------------------------------------------------------------------
# 1) Remove a logica antiga (janela de tempo unica), obsoleta
# ---------------------------------------------------------------------------
delete_if_exists("src/com/xaulinxs/customizations/cinematic/AllAppsEnterCascadeState.kt")

# ---------------------------------------------------------------------------
# 2) Nova logica: deteccao de mudanca de direcao, estados separados para
#    abrir/fechar o drawer vs rolar a lista de icones
# ---------------------------------------------------------------------------
write_if_absent(
    "src/com/xaulinxs/customizations/cinematic/AllAppsCascadeTrigger.kt",
    '''/*
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
''',
)

# ---------------------------------------------------------------------------
# 3) AllAppsTransitionController.java: reverte hook antigo, aplica o novo
# ---------------------------------------------------------------------------
replace_once(
    "src/com/android/launcher3/allapps/AllAppsTransitionController.java",
    """        // XaulinXs Customizations: detecta o INÍCIO real da abertura do
        // drawer (estava fechado/quase fechado, agora começou a abrir) e
        // ativa a janela de cascata de entrada nos ícones — ver
        // AllAppsEnterCascadeState para o motivo de não disparar isso
        // direto no adapter.
        if (previousProgress >= 0.98f && mProgress < 0.98f) {
            com.xaulinxs.customizations.cinematic.AllAppsEnterCascadeState.startWindow();
        }""",
    """        // XaulinXs Customizations: dispara o giro 720° em cascata sempre
        // que a DIREÇÃO do gesto de abrir/fechar o drawer muda — mesmo no
        // meio do caminho, não só ao cruzar totalmente aberto/fechado.
        // Substitui a versão anterior (janela de tempo única), que quase
        // nunca disparava com toques rápidos e parciais.
        if (mAppsView != null) {
            com.xaulinxs.customizations.cinematic.AllAppsCascadeTrigger
                    .onProgressChanged(previousProgress, mProgress, mAppsView);
            if (mProgress <= 0f || mProgress >= 1f) {
                com.xaulinxs.customizations.cinematic.AllAppsCascadeTrigger.reset();
            }
        }""",
    "AllAppsTransitionController: troca janela de tempo por deteccao de direcao",
    required=False,
)

# ---------------------------------------------------------------------------
# 4) BaseAllAppsAdapter.java: remove o hook antigo (inutil agora)
# ---------------------------------------------------------------------------
replace_once(
    "src/com/android/launcher3/allapps/BaseAllAppsAdapter.java",
    """                // XaulinXs Customizations: giro 720° em cascata ao abrir o
                // app drawer, portado do RetroPlayer (perfil
                // NOW_PLAYING_ENTER). Só dispara durante a janela real de
                // abertura do drawer (AllAppsEnterCascadeState) — nunca
                // durante reciclagem normal de scroll, que também passa
                // por aqui. Puramente aditivo: reset()/applyFromApplicationInfo
                // acima já configuraram o ícone normalmente antes disso.
                if (com.xaulinxs.customizations.cinematic.AllAppsEnterCascadeState.isActive()) {
                    com.xaulinxs.customizations.cinematic.AllAppsIconEnterEffect
                            .animateEnter(icon, position);
                }
                break;
            }""",
    """                // XaulinXs Customizations: giro 720° em cascata REMOVIDO
                // daqui — agora disparado direto pelo AllAppsTransitionController
                // via AllAppsCascadeTrigger, reagindo à mudança de direção
                // do gesto de abrir/fechar (ver AllAppsCascadeTrigger.kt).
                // onBindViewHolder não é o lugar certo porque só roda na
                // reciclagem, não necessariamente quando a view já está
                // visível na tela no momento do toque.
                break;
            }""",
    "BaseAllAppsAdapter: remove hook antigo de cascata (onBindViewHolder)",
    required=False,
)

# ---------------------------------------------------------------------------
# 5) AllAppsRecyclerView.java: motion blur + cascata tambem no scroll da
#    lista de icones dentro do drawer ja aberto
# ---------------------------------------------------------------------------
replace_once(
    "src/com/android/launcher3/allapps/AllAppsRecyclerView.java",
    """    @Override
    public void onScrolled(int dx, int dy) {
        super.onScrolled(dx, dy);
        mCumulativeVerticalScroll += dy;
    }""",
    """    @Override
    public void onScrolled(int dx, int dy) {
        super.onScrolled(dx, dy);
        mCumulativeVerticalScroll += dy;
        // XaulinXs Customizations: motion blur + aberração cromática ao
        // rolar a lista de ícones do app drawer, mesmo motor já usado no
        // scroll de páginas do Workspace (feature 2) — reaproveitado sem
        // mudanças. Usa um acumulador PRÓPRIO (não mCumulativeVerticalScroll,
        // que o AOSP reseta a cada novo toque — resetar quebraria a
        // suavização de velocidade do motor cinematográfico). Puramente
        // observacional, roda depois do scroll real.
        mXaulinXsScrollAccumulator += dy;
        com.xaulinxs.customizations.cinematic.CinematicScrollVelocityEffect
                .onScrollPositionChanged(this, (float) mXaulinXsScrollAccumulator);
        // XaulinXs Customizations: giro 720° em cascata também ao rolar
        // (não só ao abrir/fechar o drawer inteiro) — dispara nos ícones
        // atualmente visíveis quando a direção do scroll muda (para cima
        // vs para baixo), mesma lógica de detecção de direção usada na
        // abertura/fechamento.
        com.xaulinxs.customizations.cinematic.AllAppsCascadeTrigger
                .onScrollDirectionChanged(dy, this);
    }

    // XaulinXs Customizations: acumulador de posição independente, ver
    // comentário em onScrolled acima.
    private int mXaulinXsScrollAccumulator = 0;""",
    "AllAppsRecyclerView: motion blur + cascata no scroll da lista de icones",
)

replace_once(
    "src/com/android/launcher3/allapps/AllAppsRecyclerView.java",
    """            case SCROLL_STATE_IDLE:
                mgr.logger().sendToInteractionJankMonitor(
                        LAUNCHER_ALLAPPS_VERTICAL_SWIPE_END, this);
                logCumulativeVerticalScroll();
                break;""",
    """            case SCROLL_STATE_IDLE:
                mgr.logger().sendToInteractionJankMonitor(
                        LAUNCHER_ALLAPPS_VERTICAL_SWIPE_END, this);
                logCumulativeVerticalScroll();
                // XaulinXs Customizations: scroll da lista de ícones parou
                // — zera o motion blur/aberração cromática e a direção
                // conhecida da cascata.
                com.xaulinxs.customizations.cinematic.CinematicScrollVelocityEffect
                        .onScrollSettled(this);
                com.xaulinxs.customizations.cinematic.AllAppsCascadeTrigger.reset();
                break;""",
    "AllAppsRecyclerView: zera efeitos ao parar de rolar (SCROLL_STATE_IDLE)",
)

print("\nOK - Cascata e motion blur agora reagem a MUDANCA DE DIRECAO (nao mais a uma")
print("janela de tempo unica), tanto ao abrir/fechar o drawer quanto ao rolar a lista")
print("de icones dentro dele.")
print("Proximo passo: ./gradlew assembleNoQuickstepDebug")
