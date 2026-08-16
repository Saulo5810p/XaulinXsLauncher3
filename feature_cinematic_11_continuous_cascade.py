#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XaulinXs Customizations — Feature 11/N: duas mudancas de comportamento
na cascata giratoria 720 graus, pedidas pelo usuario apos aprovar as
features 9 e 10.

MUDANCA 1 (Workspace): o disparo da cascata deixa de acontecer durante
o proprio arrasto (mudanca de direcao) e passa a ser ADIADO ate o
scroll ASSENTAR de vez. Motivo: a cascata suavizada do item 1 demora
para "cair" e estava ofuscando o efeito de coverflow 3D
(CinematicCoverFlowEffect) enquanto as paginas ainda se moviam. Agora a
cascata so dispara depois que a pagina ja parou, como um "acabamento".

MUDANCA 2 (App Drawer apenas — Widget Picker e Workspace NAO mudam):
a cascata deixa de ser SEQUENCIAL (um icone de cada vez, com stagger)
e passa a disparar em TODOS os icones visiveis JUNTOS, continuamente,
a cada evento de scroll (todo onScrolled/onProgressChanged) — nao so
na mudanca de direcao. Isso vale tanto para abrir/fechar o drawer
quanto para rolar a lista de icones ja aberta. A velocidade do giro
tambem aumenta (stiffness 15f -> 55f so nesse modo) para "adequar ao
scroll do dedo". Decisao do usuario: se ja existe um giro em andamento
num icone, um novo giro so comeca quando o anterior TERMINAR (evita
picotar a rotacao interrompida no meio).

NOVO (efeito adicional, nao estava nos itens originais): quando um
WIDGET e adicionado a Workspace, ele ganha o mesmo efeito leve de
entrada (giro 720 + escala + fade) que os icones do App Drawer tem —
disparo unico, giro individual normal (nao o modo continuo).

Arquivos SOBRESCRITOS por completo (mudancas extensas, mais seguro que
patches fragmentados):
  - src/com/xaulinxs/customizations/cinematic/AllAppsIconEnterEffect.kt
  - src/com/xaulinxs/customizations/cinematic/AllAppsCascadeTrigger.kt
  - src/com/xaulinxs/customizations/cinematic/WorkspaceCascadeTrigger.kt

Arquivos com PATCH pontual (mudancas pequenas e localizadas):
  - src/com/android/launcher3/PagedView.java (reset() agora recebe
    `this` e dispara a cascata do Workspace se houve movimento)
  - src/com/android/launcher3/Launcher.java (novo hook de efeito de
    entrada no widget recem-adicionado)

PRE-REQUISITO: as features 9 e 10 (WorkspaceCascadeTrigger.kt e
WorkspaceDepthBlurEffect.kt) precisam ja estar aplicadas — este script
verifica isso antes de mexer em qualquer coisa e aborta com uma
mensagem clara se nao estiverem.

Idempotente: pode rodar varias vezes sem duplicar ou quebrar nada. Se
os arquivos .kt ja estiverem no conteudo final esperado, pula a
escrita. Se o patch do PagedView/Launcher ja foi aplicado, pula.

Uso:
    python3 feature_cinematic_11_continuous_cascade.py /caminho/do/repo
    (ou rode de dentro da raiz do repo sem argumento)
"""

import os
import sys

PAGEDVIEW_REL_PATH = "src/com/android/launcher3/PagedView.java"
LAUNCHER_REL_PATH = "src/com/android/launcher3/Launcher.java"
ICON_ENTER_REL_PATH = "src/com/xaulinxs/customizations/cinematic/AllAppsIconEnterEffect.kt"
CASCADE_TRIGGER_REL_PATH = "src/com/xaulinxs/customizations/cinematic/AllAppsCascadeTrigger.kt"
WORKSPACE_CASCADE_REL_PATH = "src/com/xaulinxs/customizations/cinematic/WorkspaceCascadeTrigger.kt"

MARKER_PAGEDVIEW_RESET = "WorkspaceCascadeTrigger.reset(this);"
MARKER_LAUNCHER_WIDGET_HOOK = "// XAULINXS_WIDGET_ADD_ENTER_HOOK"

ICON_ENTER_CONTENT = '/*\n * XaulinXs Customizations — não faz parte do AOSP original.\n *\n * Giro 720° + motion blur + aberração cromática na entrada de cada ícone\n * do app drawer, portado do perfil NOW_PLAYING_ENTER do projeto irmão\n * RetroPlayer Compose (NowPlayingScreen.kt): rotation (eixo Z) decrescendo de\n * maxRotationDegrees até 0 conforme o progresso avança, escala com\n * overshoot senoidal, alpha fade-in, blur/aberração cromática máximos no\n * início e some ao final — mesma matemática, só trocando Animatable+spring\n * do Compose por SpringAnimation (androidx.dynamicanimation), o\n * equivalente nativo View System.\n *\n * Efeito em CASCATA: cada ícone recebe um atraso proporcional à sua\n * posição no grid, criando a sensação de "surgir" em sequência em vez de\n * todos ao mesmo tempo — usado pelo Workspace e pelo Widget Picker.\n *\n * ATUALIZAÇÃO: o App Drawer agora chama animateEnter repetidamente em\n * sequência rápida (a cada frame de scroll, positionInGrid sempre 0, ver\n * AllAppsCascadeTrigger). Nesse modo contínuo, a spring usa stiffness\n * mais alta (giro mais rápido, ver STIFFNESS_CONTINUOUS) — pedido do\n * usuário para "adequar a velocidade ao scroll do dedo", já que o giro\n * se repete a cada evento em vez de rodar uma única vez. runSpring\n * cancela qualquer spring residual antes de iniciar uma nova (rastreada\n * via WeakHashMap, não View.setTag — ver activeSprings abaixo).\n */\npackage com.xaulinxs.customizations.cinematic\n\nimport android.os.Build\nimport android.view.View\nimport androidx.dynamicanimation.animation.FloatValueHolder\nimport androidx.dynamicanimation.animation.SpringAnimation\nimport androidx.dynamicanimation.animation.SpringForce\nimport kotlin.math.PI\nimport kotlin.math.max\nimport kotlin.math.sin\n\nobject AllAppsIconEnterEffect {\n\n    // Rastreia a SpringAnimation em andamento por ícone, pra poder\n    // cancelar a anterior ao reiniciar continuamente (App Drawer chama\n    // animateEnter em sequência rápida, a cada frame de scroll).\n    // IMPORTANTE: NÃO usar View.setTag()/getTag() pra isso — o próprio\n    // Launcher3 já usa a tag sem chave de cada BubbleTextView pra\n    // guardar o ItemInfo do app (ver BubbleTextView.getTag()); sobrescrever\n    // isso quebraria clique/drag dos ícones. WeakHashMap evita vazamento\n    // de memória sem tocar na tag da view.\n    private val activeSprings = java.util.WeakHashMap<View, SpringAnimation>()\n\n    // Mesmos valores do perfil NOW_PLAYING_ENTER (CinematicProfile.kt do\n    // RetroPlayer): mass=1.5, stiffness=130, damping=6.5, rotação 720°,\n    // overshoot 1.5x, blur/aberração cromática altos.\n    private const val MAX_ROTATION_DEGREES = 720f\n    private const val OVERSHOOT_SCALE = 1.5f\n    private const val BLUR_MULTIPLIER = 3.6f\n    private const val CHROMATIC_MULTIPLIER = 3.0f\n    private const val VIGNETTE_MULTIPLIER = 1.0f\n\n    // Atraso entre o início da animação de cada ícone consecutivo na\n    // cascata — pequeno o bastante para não atrasar demais o último ícone\n    // visível, grande o bastante para a sequência ser perceptível.\n    // Usado só no modo stagger (Workspace/Widget Picker); modo contínuo\n    // (App Drawer) sempre usa delayMs=0 (positionInGrid=0).\n    private const val STAGGER_DELAY_MS = 110L // suavizado (era 18L) — cascata varre bem mais devagar\n    private const val MAX_STAGGER_ITEMS = 30 // evita atraso enorme em grids grandes\n\n    // Modo contínuo (App Drawer): stiffness maior que a padrão (15f) —\n    // giro mais rápido/ágil, adequado ao ritmo do scroll do dedo, já que\n    // aqui o giro se repete a cada evento em vez de rodar uma única vez.\n    // Continua reaproveitando a mesma curva (dampingRatio) do item 1.\n    private const val STIFFNESS_CONTINUOUS = 55f\n    private const val STIFFNESS_STAGGER = 15f // Workspace/Widget Picker, inalterado (item 1)\n\n    /**\n     * Dispara a animação de entrada em cascata no ícone, com atraso\n     * proporcional à posição dele no grid (Workspace/Widget Picker,\n     * stagger sequencial normal).\n     *\n     * MODO CONTÍNUO (App Drawer, chamado repetidamente em sequência\n     * rápida a todo frame de scroll): decisão do usuário — se já existe\n     * uma spring EM ANDAMENTO neste ícone, a chamada é ignorada (não\n     * reseta, não reinicia no meio). Um giro novo só começa quando o\n     * anterior já tiver terminado. Isso evita picotar a rotação\n     * (interrompida antes de completar) quando os eventos de scroll vêm\n     * mais rápido que a duração da spring. Sinalizado explicitamente via\n     * `continuous` — NÃO inferido de positionInGrid==0, porque outros\n     * chamadores (widget recém-adicionado à Workspace) também usam\n     * posição 0 sem quererem o modo contínuo.\n     */\n    @JvmStatic\n    @JvmOverloads\n    fun animateEnter(icon: View, positionInGrid: Int, continuous: Boolean = false) {\n        if (continuous && activeSprings[icon]?.isRunning == true) {\n            return\n        }\n\n        val staggerIndex = positionInGrid.coerceIn(0, MAX_STAGGER_ITEMS)\n        val delayMs = if (continuous) 0L else staggerIndex * STAGGER_DELAY_MS\n\n        // Estado inicial: escondido/girado, antes da spring rodar.\n        icon.rotation = MAX_ROTATION_DEGREES\n        icon.rotationY = 30f\n        icon.scaleX = 0.05f\n        icon.scaleY = 0.05f\n        icon.alpha = 0f\n\n        icon.postDelayed({ runSpring(icon, continuous) }, delayMs)\n    }\n\n    private fun runSpring(icon: View, isContinuousMode: Boolean) {\n        // Segunda camada de segurança: animateEnter já evita chegar aqui\n        // com uma spring em andamento no modo contínuo (App Drawer), mas\n        // Workspace/Widget Picker ainda podem, em teoria, re-disparar\n        // via postDelayed antes do fim — cancela qualquer resíduo antes\n        // de iniciar uma nova.\n        activeSprings[icon]?.cancel()\n\n        // FloatValueHolder vai de 0 a 1 (não 1000 — mSpring já trabalha\n        // bem em escala 0..1, sem necessidade de normalizar depois).\n        // Valores de stiffness/dampingRatio escolhidos para reproduzir o\n        // "bounce" perceptível do perfil NOW_PLAYING_ENTER do RetroPlayer\n        // (overshoot visível, mas sem oscilar demais) — as unidades do\n        // SpringForce do Android (stiffness absoluta, dampingRatio 0..1)\n        // não correspondem 1:1 às unidades do spring() do Compose, então\n        // isso é uma calibração visual equivalente, não uma conversão\n        // matemática direta dos mesmos números.\n        val holder = FloatValueHolder(0f)\n        val spring = SpringAnimation(holder).apply {\n            setSpring(\n                SpringForce(1f).apply {\n                    stiffness = if (isContinuousMode) STIFFNESS_CONTINUOUS else STIFFNESS_STAGGER\n                    dampingRatio = 0.78f // overshoot bem mais contido/suave\n                }\n            )\n            setStartVelocity(0f)\n            minimumVisibleChange = 0.001f\n        }\n\n        activeSprings[icon] = spring\n\n        spring.addUpdateListener { _, value, _ ->\n            applyFrame(icon, value.coerceIn(0f, 1.4f)) // permite overshoot > 1\n        }\n        spring.addEndListener { animation, canceled, _, _ ->\n            if (!canceled) {\n                applyFrame(icon, 1f)\n            }\n            if (activeSprings[icon] === animation) {\n                activeSprings.remove(icon)\n            }\n        }\n        spring.start()\n    }\n\n    private fun applyFrame(icon: View, progress: Float) {\n        val remaining = max(0f, 1f - progress)\n\n        if (remaining <= 0.005f) {\n            icon.rotation = 0f\n            icon.rotationY = 0f\n            icon.scaleX = 1f\n            icon.scaleY = 1f\n            icon.alpha = 1f\n            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {\n                icon.setRenderEffect(null)\n            }\n            return\n        }\n\n        icon.rotation = remaining * MAX_ROTATION_DEGREES\n        icon.rotationY = remaining * 30f\n\n        val enterScale = (1f + (OVERSHOOT_SCALE - 1f) *\n                sin(progress * PI.toFloat()) * remaining + (1f - remaining))\n            .coerceAtLeast(0.05f)\n        icon.scaleX = enterScale\n        icon.scaleY = enterScale\n        icon.alpha = progress.coerceIn(0f, 1f)\n\n        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {\n            val w = icon.width.toFloat().coerceAtLeast(50f)\n            val h = icon.height.toFloat().coerceAtLeast(50f)\n            val effect = CinematicShader.createCinematicEffect(\n                width = w,\n                height = h,\n                rotationSpeed = remaining * 4.0f,\n                scaleFactor = enterScale,\n                blurIntensity = remaining * BLUR_MULTIPLIER,\n                chromaticShift = remaining * CHROMATIC_MULTIPLIER,\n                vignetteIntensity = remaining * VIGNETTE_MULTIPLIER\n            )\n            icon.setRenderEffect(effect)\n        }\n    }\n}\n'
CASCADE_TRIGGER_CONTENT = '/*\n * XaulinXs Customizations — não faz parte do AOSP original.\n *\n * ATUALIZAÇÃO (pedido do usuário): a versão anterior disparava a cascata\n * SEQUENCIAL (um ícone de cada vez, com stagger de posição) só na\n * MUDANÇA DE DIREÇÃO do gesto. Isso criava um delay perceptível entre o\n * primeiro e o último ícone, e só reiniciava a cascata quando o dedo\n * invertia de sentido. Agora o comportamento é: TODOS os ícones visíveis\n * giram JUNTOS (sem stagger — positionInGrid sempre 0), e a animação é\n * DISPARADA DE NOVO A CADA EVENTO DE MOVIMENTO (todo onScrolled/todo\n * onProgressChanged), não só na mudança de direção — criando uma\n * "cascata infinita" enquanto o dedo desliza, pra cima ou pra baixo,\n * tanto rolando a lista já aberta quanto abrindo/fechando o drawer\n * inteiro. AllAppsIconEnterEffect.animateEnter cancela a spring anterior\n * de cada ícone antes de reiniciar (ver runSpring), evitando springs\n * acumuladas/conflitantes ao reiniciar em todo frame.\n *\n * Efeito reservado ao APP DRAWER apenas — Widget Picker mantém o\n * comportamento sequencial/stagger anterior de propósito (o usuário\n * achou o resultado "perfeito" lá, mais devagar item a item), e o\n * Workspace tem lógica própria e SEPARADA (WorkspaceCascadeTrigger,\n * disparo adiado até o scroll assentar, para não ofuscar o coverflow 3D).\n *\n * Dispara diretamente nas child views VISÍVEIS NA TELA a cada evento, em\n * vez de depender de onBindViewHolder (que só roda quando o RecyclerView\n * recicla uma view — nem sempre coincide com "a view está visível agora").\n */\npackage com.xaulinxs.customizations.cinematic\n\nimport android.view.View\nimport android.view.ViewGroup\nimport com.android.launcher3.BubbleTextView\n\nobject AllAppsCascadeTrigger {\n\n    /**\n     * Chamar a cada mudança de progresso do drawer (mesmo ponto onde\n     * CinematicScrollVelocityEffect já é alimentado). Dispara a cascata\n     * SEM STAGGER (todos os ícones visíveis juntos) em TODO evento de\n     * movimento — não só na mudança de direção — enquanto o drawer está\n     * de fato se movendo (abrindo ou fechando).\n     */\n    @JvmStatic\n    fun onProgressChanged(previousProgress: Float, newProgress: Float, container: ViewGroup) {\n        if (previousProgress == newProgress) return\n        triggerOnVisibleIcons(container)\n    }\n\n    /**\n     * Chamar a cada onScrolled(dx, dy) da lista de ícones do app drawer\n     * já aberto. Dispara a cascata SEM STAGGER (todos os ícones visíveis\n     * juntos) em TODO evento de scroll (dy != 0) — pra cima ou pra baixo\n     * — não só na mudança de direção.\n     */\n    @JvmStatic\n    fun onScrollDirectionChanged(dy: Int, container: ViewGroup) {\n        if (dy == 0) return\n        triggerOnVisibleIcons(container)\n    }\n\n    /**\n     * Mantido por compatibilidade com os pontos de chamada existentes\n     * (AllAppsRecyclerView, AllAppsTransitionController chamam reset() ao\n     * assentar) — não há mais estado de direção pra zerar, mas a função\n     * continua existindo pra não quebrar essas chamadas.\n     */\n    @JvmStatic\n    fun reset() {\n        // Sem estado a resetar — a cascata contínua não guarda direção.\n    }\n\n    private fun triggerOnVisibleIcons(container: ViewGroup) {\n        val icons = ArrayList<View>()\n        collectVisibleBubbleTextViews(container, icons)\n        // positionInGrid = 0 pra todos: remove o stagger, todos giram\n        // juntos (delayMs = 0, modo contínuo explícito — ver\n        // AllAppsIconEnterEffect.animateEnter).\n        icons.forEach { icon ->\n            AllAppsIconEnterEffect.animateEnter(icon, 0, continuous = true)\n        }\n    }\n\n    private fun collectVisibleBubbleTextViews(view: View, out: MutableList<View>) {\n        if (view is BubbleTextView && view.visibility == View.VISIBLE) {\n            out.add(view)\n            return\n        }\n        if (view is ViewGroup) {\n            for (i in 0 until view.childCount) {\n                collectVisibleBubbleTextViews(view.getChildAt(i), out)\n            }\n        }\n    }\n}\n'
WORKSPACE_CASCADE_CONTENT = '/*\n * XaulinXs Customizations — não faz parte do AOSP original.\n *\n * Leva o efeito de cascata giratória 720° (AllAppsIconEnterEffect, já usado\n * no app drawer e no widget picker) para o Workspace: ícones E widgets\n * das páginas do launcher também giram em cascata ao rolar entre telas.\n *\n * ATUALIZAÇÃO (pedido do usuário): a versão anterior disparava a cada\n * MUDANÇA DE DIREÇÃO durante o próprio arrasto (igual ao AllApps). Isso\n * ofuscava o efeito de coverflow 3D (CinematicCoverFlowEffect) — a\n * cascata demora pra "cair" (física suavizada do item 1: stiffness 15f,\n * stagger 110ms) e competia visualmente com a rotação 3D das páginas\n * enquanto elas ainda estavam se movendo. Agora o disparo é ADIADO: só\n * acontece quando o scroll ASSENTA de vez (mesmo ponto de\n * onScrollSettled/reset já usado pelo blur de velocidade), e só se de\n * fato houve movimento de página desde o último assentamento — não mais\n * durante o arrasto. Isso libera o coverflow para ser visto sem\n * concorrência, e a cascata vira um "acabamento" depois que a página já\n * está parada.\n *\n * Diferença de arquitetura em relação ao AllApps: lá, os ícones "surgem"\n * de verdade (drawer abrindo, RecyclerView populando) e a cascata reage\n * ao próprio gesto em tempo real. No Workspace as páginas vizinhas já\n * ficam sempre montadas por baixo do pano — não há um momento nativo de\n * "entrada", e agora nem reage mais ao gesto em si. Por isso a cascata\n * aqui dispara sobre as views JÁ EXISTENTES, sem tocar em nenhuma lógica\n * de posicionamento, e só depois que o movimento parou.\n *\n * Escopo por página (confirmado com o usuário, mantido na atualização\n * acima): quando dispara, a cascata roda em TODAS as páginas visíveis na\n * tela naquele momento — a página que ficou central E a(s) que ainda\n * está(ão) entrando/saindo pela lateral — não só a página central.\n *\n * Widgets: diferente do AllApps (só BubbleTextView), aqui o container de\n * cada página (ShortcutAndWidgetContainer) mistura BubbleTextView e\n * LauncherAppWidgetHostView — os dois tipos são coletados e giram juntos.\n */\npackage com.xaulinxs.customizations.cinematic\n\nimport android.view.View\nimport android.view.ViewGroup\nimport com.android.launcher3.BubbleTextView\nimport com.android.launcher3.widget.LauncherAppWidgetHostView\n\nobject WorkspaceCascadeTrigger {\n\n    // Não guardamos mais a direção pra disparar durante o arrasto — só\n    // marcamos que houve movimento, para decidir no assentamento se vale\n    // a pena disparar a cascata (evita disparar em toques que nem\n    // chegaram a mover a página).\n    @Volatile\n    private var hasPendingMovement = false\n\n    /**\n     * Chamar a cada mudança de posição de scroll do Workspace (arrasto\n     * manual ou fling — mesmos pontos já alimentando\n     * CinematicScrollVelocityEffect.onScrollPositionChanged em\n     * PagedView.java). Não dispara mais a cascata aqui — só registra que\n     * houve movimento, para o disparo real acontecer em reset(), quando\n     * o scroll assenta de vez.\n     */\n    @JvmStatic\n    fun onScrollPositionChanged(pages: ViewGroup, newScroll: Float, previousScroll: Float) {\n        if (!newScroll.isFinite() || !previousScroll.isFinite()) return\n        if (newScroll == previousScroll) return\n        hasPendingMovement = true\n    }\n\n    /**\n     * Chamar quando o scroll assenta de vez (mesmo ponto do\n     * onScrollSettled do blur de velocidade). Dispara a cascata nas\n     * páginas atualmente visíveis SE houve movimento desde o último\n     * assentamento — evita disparar em toques que não moveram a página.\n     * `pages` é o próprio PagedView/Workspace (ViewGroup cujos filhos\n     * diretos são as CellLayout/páginas).\n     */\n    @JvmStatic\n    fun reset(pages: ViewGroup) {\n        if (hasPendingMovement) {\n            triggerOnVisiblePages(pages)\n        }\n        hasPendingMovement = false\n    }\n\n    private fun triggerOnVisiblePages(pages: ViewGroup) {\n        for (i in 0 until pages.childCount) {\n            val page = pages.getChildAt(i)\n            // Só páginas de fato visíveis na tela agora (evita disparar em\n            // páginas fora da faixa visível que o PagedView mantém\n            // infladas para scroll suave, mas que o usuário não está vendo).\n            if (page.visibility != View.VISIBLE || !page.getLocalVisibleRect(TEMP_RECT)) continue\n\n            val items = ArrayList<View>()\n            collectIconsAndWidgets(page, items)\n            items.forEachIndexed { index, item ->\n                AllAppsIconEnterEffect.animateEnter(item, index)\n            }\n        }\n    }\n\n    private val TEMP_RECT = android.graphics.Rect()\n\n    private fun collectIconsAndWidgets(view: View, out: MutableList<View>) {\n        if ((view is BubbleTextView || view is LauncherAppWidgetHostView) &&\n            view.visibility == View.VISIBLE\n        ) {\n            out.add(view)\n            return\n        }\n        if (view is ViewGroup) {\n            for (i in 0 until view.childCount) {\n                collectIconsAndWidgets(view.getChildAt(i), out)\n            }\n        }\n    }\n}\n\n// XAULINXS_WORKSPACE_CASCADE_TRIGGER_FILE\n'


def find_repo_root(start):
    candidates = [start] + ([os.path.join(start, d) for d in os.listdir(start)] if os.path.isdir(start) else [])
    for c in candidates:
        if os.path.isfile(os.path.join(c, PAGEDVIEW_REL_PATH)):
            return c
    return None


def check_prerequisites(repo_root):
    workspace_cascade_path = os.path.join(repo_root, WORKSPACE_CASCADE_REL_PATH)
    if not os.path.isfile(workspace_cascade_path):
        print("[!] ERRO: " + WORKSPACE_CASCADE_REL_PATH + " nao encontrado.")
        print("    Este script depende das features 9 e 10 ja aplicadas")
        print("    (cascata do Workspace e blur pesado por posicao).")
        print("    Rode feature_cinematic_9_workspace_cascade.py e")
        print("    feature_cinematic_10_workspace_depth_blur.py primeiro,")
        print("    ou confirme que o repo remoto esta atualizado (git pull).")
        return False
    return True


def write_kt_file(repo_root, rel_path, content, label):
    path = os.path.join(repo_root, rel_path)
    if not os.path.isfile(path):
        print("[!] ERRO: " + rel_path + " nao encontrado — abortando esta escrita.")
        return False
    with open(path, "r", encoding="utf-8") as f:
        existing = f.read()
    if existing == content:
        print("[=] " + label + " ja esta no conteudo final esperado — pulando.")
        return True
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] " + label + " atualizado.")
    return True


def patch_pagedview(repo_root):
    path = os.path.join(repo_root, PAGEDVIEW_REL_PATH)
    if not os.path.isfile(path):
        print("[!] ERRO: " + PAGEDVIEW_REL_PATH + " nao encontrado — abortando este patch.")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if MARKER_PAGEDVIEW_RESET in content:
        print("[=] PagedView.java ja tem o patch do reset adiado — pulando.")
        return True

    old_block = (
        "        // XaulinXs Customizations: reseta a direção conhecida da cascata\n"
        "        // do Workspace junto com o reset do blur de velocidade.\n"
        "        // XAULINXS_WORKSPACE_CASCADE_HOOK_RESET\n"
        "        com.xaulinxs.customizations.cinematic.WorkspaceCascadeTrigger.reset();\n"
    )
    if old_block not in content:
        print("[!] ERRO: ancora do reset (feature 9) nao encontrada em PagedView.java.")
        print("    O arquivo pode ja ter sido modificado de forma diferente do esperado.")
        print("    Nenhuma alteracao foi feita — revise manualmente.")
        return False
    if content.count(old_block) > 1:
        print("[!] ERRO: ancora aparece mais de uma vez — abortando por seguranca.")
        return False

    new_block = (
        "        // XaulinXs Customizations: scroll assentou de vez — dispara a\n"
        "        // cascata do Workspace AGORA (adiada até aqui, pedido do\n"
        "        // usuário) se houve movimento, e zera o estado.\n"
        "        // XAULINXS_WORKSPACE_CASCADE_HOOK_RESET\n"
        "        com.xaulinxs.customizations.cinematic.WorkspaceCascadeTrigger.reset(this);\n"
    )
    content = content.replace(old_block, new_block, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] PagedView.java: reset() adiado aplicado.")
    return True


def patch_launcher(repo_root):
    path = os.path.join(repo_root, LAUNCHER_REL_PATH)
    if not os.path.isfile(path):
        print("[!] ERRO: " + LAUNCHER_REL_PATH + " nao encontrado — abortando este patch.")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if MARKER_LAUNCHER_WIDGET_HOOK in content:
        print("[=] Launcher.java ja tem o hook de entrada do widget — pulando.")
        return True

    old_block = (
        "        hostView.setVisibility(View.VISIBLE);\n"
        "        mItemInflater.prepareAppWidget(hostView, launcherInfo);\n"
        "        if (hostView.getParent() == null) {\n"
        "            mWorkspace.addInScreen(hostView, launcherInfo);\n"
        "        }\n"
    )
    if old_block not in content:
        print("[!] ERRO: ancora do addInScreen nao encontrada em Launcher.java.")
        print("    O arquivo pode ter mudado de estrutura — revise manualmente.")
        return False
    if content.count(old_block) > 1:
        print("[!] ERRO: ancora aparece mais de uma vez — abortando por seguranca.")
        return False

    new_block = (
        "        hostView.setVisibility(View.VISIBLE);\n"
        "        mItemInflater.prepareAppWidget(hostView, launcherInfo);\n"
        "        if (hostView.getParent() == null) {\n"
        "            mWorkspace.addInScreen(hostView, launcherInfo);\n"
        "            // XaulinXs Customizations: efeito leve de entrada (giro 720°\n"
        "            // + escala + fade, mesmo AllAppsIconEnterEffect usado nos\n"
        "            // ícones do app drawer) no widget recém-adicionado à\n"
        "            // Workspace — pedido do usuário, dispara uma única vez.\n"
        "            // continuous NÃO é passado (fica no default false) — isso é\n"
        "            // um giro individual normal, não o modo contínuo do App\n"
        "            // Drawer (que só ativa quando explicitamente pedido via\n"
        "            // AllAppsCascadeTrigger).\n"
        "            " + MARKER_LAUNCHER_WIDGET_HOOK + "\n"
        "            com.xaulinxs.customizations.cinematic.AllAppsIconEnterEffect\n"
        "                    .animateEnter(hostView, 0);\n"
        "        }\n"
    )
    content = content.replace(old_block, new_block, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] Launcher.java: hook de entrada do widget aplicado.")
    return True


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else "."
    repo_root = find_repo_root(os.path.abspath(start))
    if repo_root is None:
        print("[!] ERRO: nao encontrei " + PAGEDVIEW_REL_PATH + " a partir de \'" + start + "\'.")
        print("    Rode este script de dentro da raiz do repo, ou passe o caminho como argumento.")
        sys.exit(1)

    print("Repo detectado em: " + repo_root + "\n")

    if not check_prerequisites(repo_root):
        sys.exit(1)

    ok = True
    ok &= write_kt_file(repo_root, ICON_ENTER_REL_PATH, ICON_ENTER_CONTENT, "AllAppsIconEnterEffect.kt")
    ok &= write_kt_file(repo_root, CASCADE_TRIGGER_REL_PATH, CASCADE_TRIGGER_CONTENT, "AllAppsCascadeTrigger.kt")
    ok &= write_kt_file(repo_root, WORKSPACE_CASCADE_REL_PATH, WORKSPACE_CASCADE_CONTENT, "WorkspaceCascadeTrigger.kt")
    ok &= patch_pagedview(repo_root)
    ok &= patch_launcher(repo_root)

    print()
    if ok:
        print("Concluido. Rode ./gradlew assembleDebug para compilar.")
    else:
        print("Concluido com erros — revise as mensagens [!] acima antes de compilar.")
        sys.exit(1)


if __name__ == "__main__":
    main()
