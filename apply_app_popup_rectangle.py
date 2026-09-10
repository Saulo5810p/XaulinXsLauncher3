#!/usr/bin/env python3
"""
XaulinXs Customizations - Fase 3 (popup de app: retangulo real).

Resolve os 4 problemas reportados no popup de app (long-press num icone
de app na workspace / hotseat / menu de aplicativos):

1) "O retangulo dos apps com as opcoes nao e um retangulo": cada item
   (deep_shortcut / system_shortcut) tinha fundo (middle_item_primary)
   e elevacao PROPRIOS, dentro de um container que TAMBEM tinha fundo
   (popup_background) - resultado visual: blocos soltos com sombra
   individual, nao um retangulo unico. Fix: o container do popup ganha
   um unico fundo real (xaulinxs_app_popup_sheet_background) e os itens
   passam a ser barras transparentes por cima dele.

2) "O interruptor de esconder e so um retangulo que nao faz nada":
   causa raiz real - o header usava androidx.appcompat.widget.SwitchCompat,
   mas o tema do app so define android:switchStyle (Switch NATIVO, usado
   nas Configuracoes via SwitchStyle em styles.xml), nunca o switchStyle
   do AppCompat. Sem esse estilo o SwitchCompat desenha sem trilho/thumb -
   parece um retangulo, mesmo com o listener de clique ja funcionando.
   Fix: trocado para android.widget.Switch com style="@style/SwitchStyle"
   aplicado direto na view (mesmo estilo do interruptor das Configuracoes).

3) "Nem todos os Baloes viraram Barras": Atalhos (deep shortcuts),
   Widgets, Adicionar a tela inicial e Informacoes do app ainda usavam
   deep_shortcut.xml/system_shortcut.xml originais (fundo
   middle_item_primary). Fix: novos layouts (barra transparente, sem
   elevacao propria) substituem os originais SO dentro do popup de app -
   os arquivos originais continuam intocados para qualquer outro uso
   futuro. Isso inclui tambem o modo "colapsado" (icones-apenas, usado
   quando o app tem mais de 6 atalhos+opcoes no total -
   SHORTCUT_COLLAPSE_THRESHOLD em PopupContainerWithArrow.kt):
   system_shortcut_icons_container.xml tinha o MESMO bug do problema 1
   (background=popup_background fixo + elevacao propria) - sem este
   fix, quem tivesse muitos atalhos veria a fileira de icones ainda
   flutuando separada do retangulo por baixo dela. Os icones
   individuais (system_shortcut_icon_only/_start/_end) ja nao tinham
   fundo solido proprio (soletam so via ripple), entao nao precisaram
   de layout novo - so o container deles.

4) "Cor manual dos Baloes nao afeta o retangulo": XaulinXsBalloonColor ja
   pintava os ITENS individuais (mColors em ArrowPopup.java), mas o fundo
   do container continuava fixo em materialColorSurfaceContainer. Fix:
   PopupContainerWithArrow aplica XaulinXsBalloonColor.getBalloonColorOverride
   no fundo do proprio container, mesmo mecanismo ja usado por
   XaulinXsOptionsSheet.applyBalloonColorBackground() no popup da workspace.

Tambem unifica a largura do popup (header usava 280dp via
xaulinxs_app_popup_width, os itens usavam 216dp via bg_popup_item_width,
e o retangulo de fundo seria ainda mais largo - 3 larguras diferentes
coexistindo, a causa raiz mais profunda do "retangulo bagunçado") em
uma unica largura nova de 320dp (xaulinxs_app_popup_sheet_width) -
tamanho de popup razoavel, nem metade da tela nem muito pequeno, como
no print do Lawnchair enviado. Isso inclui a variavel containerWidth
(usada para redimensionar cada barra em runtime): sem essa troca as
barras ficariam mais estreitas que o proprio retangulo atras delas,
sobrando espaco vazio dos dois lados dentro do popup.

O QUE NAO ESTA NESTE SCRIPT (decisao consciente de risco):
- Arrastar para baixo para fechar (o menu de aplicativos usa
  AbstractSlideInView/SingleAxisSwipeDetector para isso). O popup de app
  (PopupContainerWithArrow/ArrowPopup) ja tem hoje o gesto de "tocar fora
  fecha" (onControllerInterceptTouchEvent em PopupContainer.kt) - o
  arrastar-para-fechar especifico ficou de fora desta entrega porque
  currently PopupContainerWithArrow.onInterceptTouchEvent ja usa o
  mesmo canal de toque para o slop de arrastar shortcuts para a
  workspace; misturar os dois detectores de gesto no mesmo evento e uma
  fonte real de bug (podem competir pelo mesmo toque) e nao foi
  arriscado nesta entrega. Posso fazer como proximo passo isolado, se
  quiser.

Uso:
    python3 apply_app_popup_rectangle.py [caminho_do_repo]

Idempotente: pode rodar mais de uma vez sem duplicar nada.
"""

import hashlib
import re
import sys
from pathlib import Path

FILES_TO_CREATE = {
    "res/drawable/xaulinxs_app_popup_sheet_background.xml": """<?xml version="1.0" encoding="utf-8"?>
<!--
     XaulinXs Customizations - Fase 3 (popup de app como retângulo real).
     Fundo do retângulo único do popup de app (mesmo padrão visual do
     xaulinxs_sheet_background usado pelo popup de área vazia): cantos
     arredondados nos 4 lados (aqui NÃO é bottom sheet ancorado na borda
     da tela, então não faz sentido achatar a base). Cor de base = mesma
     cor estática usada no popup de área vazia antes da extração em
     runtime (materialColorSurfaceContainer) - a extração real (wallpaper
     ou cor manual) é aplicada em cima disso via
     PopupContainerWithArrow.applyXaulinXsSheetBackground(), o mesmo
     mecanismo já usado por XaulinXsOptionsSheet.applyBalloonColorBackground().
-->
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="rectangle">
    <solid android:color="@color/materialColorSurfaceContainer"/>
    <corners android:radius="@dimen/xaulinxs_app_popup_sheet_corner_radius" />
</shape>
""",
    "res/drawable/xaulinxs_app_popup_row_bg.xml": """<?xml version="1.0" encoding="utf-8"?>
<!--
     XaulinXs Customizations - Fase 3 (Balões -> Barras dentro do
     retângulo do popup de app).
     Usado nas linhas de atalho (deep shortcuts) e nas linhas de opção
     do sistema (Widgets/Adicionar à tela inicial/Informações do app).
     Sem "solid" próprio (transparente): a cor visível é a do retângulo
     único por trás (xaulinxs_app_popup_sheet_background), não mais uma
     cor por item - é isso que faz virarem barras dentro de um único
     retângulo em vez de balões/blocos soltos com sombra própria.
-->
<ripple xmlns:android="http://schemas.android.com/apk/res/android"
    android:color="?android:attr/colorControlHighlight">
    <item android:drawable="@android:color/transparent" />
</ripple>
""",
    "res/drawable/xaulinxs_app_popup_row_divider.xml": """<?xml version="1.0" encoding="utf-8"?>
<!--
     XaulinXs Customizations - Fase 3.
     Linha fina entre as barras do popup de app (mesmo espírito de
     xaulinxs_option_stroke_width usado na borda dos campos do
     cabeçalho), pra separar visualmente as opções sem precisar de
     fundo/sombra por item.
-->
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="rectangle">
    <solid android:color="?attr/popupColorTertiary"/>
</shape>
""",
    "res/layout/xaulinxs_app_popup_deep_shortcut.xml": """<?xml version="1.0" encoding="utf-8"?>
<!--
     XaulinXs Customizations - Fase 3 (Balões -> Barras).
     Equivalente a deep_shortcut.xml, mas usado só dentro do retângulo
     único do popup de app: fundo transparente
     (xaulinxs_app_popup_row_bg) e sem elevação própria - a cor visível
     vem do retângulo por trás, não mais de um balão individual.
     Reaproveita a mesma view/conteúdo interno do original (ícone +
     texto + botão de adicionar), então nenhum código de população
     (PopupPopulator/LauncherPopupLiveUpdateHandler) precisa mudar.
-->
<com.android.launcher3.shortcuts.DeepShortcutView
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:launcher="http://schemas.android.com/apk/res-auto"
    android:id="@+id/deep_shortcut_material"
    android:layout_width="match_parent"
    android:layout_height="@dimen/bg_popup_item_height"
    android:background="@drawable/xaulinxs_app_popup_row_bg"
    android:theme="@style/PopupItem" >

    <com.android.launcher3.shortcuts.DeepShortcutTextView
        style="@style/BaseIcon"
        android:id="@+id/bubble_text"
        android:background="?android:attr/selectableItemBackground"
        android:gravity="start|center_vertical"
        android:textAlignment="viewStart"
        android:paddingStart="@dimen/deep_shortcuts_text_padding_start"
        android:paddingEnd="@dimen/popup_padding_end"
        android:drawablePadding="@dimen/deep_shortcut_drawable_padding"
        android:singleLine="true"
        android:ellipsize="end"
        android:textSize="14sp"
        android:textColor="?attr/popupTextColor"
        launcher:layoutHorizontal="true"
        launcher:iconDisplay="shortcut_popup"
        launcher:iconSizeOverride="@dimen/deep_shortcut_icon_size" />

    <View
        android:id="@+id/icon"
        android:layout_width="@dimen/deep_shortcut_icon_size"
        android:layout_height="@dimen/deep_shortcut_icon_size"
        android:layout_marginStart="@dimen/popup_padding_start"
        android:layout_gravity="start|center_vertical"
        android:background="@drawable/ic_deepshortcut_placeholder"/>

    <ImageView
        android:id="@+id/deep_shortcut_add_button"
        android:layout_width="@dimen/deep_shortcut_add_button_size"
        android:layout_height="@dimen/deep_shortcut_add_button_size"
        android:layout_gravity="end|center_vertical"
        android:visibility="gone"
        android:contentDescription="@string/action_add_to_workspace"
        android:src="@drawable/ic_add_circle_filled"
        android:scaleType="center"/>

</com.android.launcher3.shortcuts.DeepShortcutView>
""",
    "res/layout/xaulinxs_app_popup_system_shortcut.xml": """<?xml version="1.0" encoding="utf-8"?>
<!--
     XaulinXs Customizations - Fase 3 (Balões -> Barras).
     Equivalente a system_shortcut.xml, mas usado só dentro do
     retângulo único do popup de app: "Widgets", "Adicionar à tela
     inicial" e "Informações do app" (as opções que ainda eram balões
     originais) agora usam este mesmo padrão de barra transparente,
     em vez de middle_item_primary.
-->
<com.android.launcher3.shortcuts.DeepShortcutView
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:id="@+id/system_shortcut"
    android:minHeight="@dimen/bg_popup_item_height"
    android:background="@drawable/xaulinxs_app_popup_row_bg"
    android:theme="@style/PopupItem" >

    <include layout="@layout/system_shortcut_content" />

</com.android.launcher3.shortcuts.DeepShortcutView>
""",
    "res/layout/xaulinxs_app_popup_deep_shortcut_container.xml": """<?xml version="1.0" encoding="utf-8"?>
<!--
     XaulinXs Customizations - Fase 3 (Balões -> Barras).
     Equivalente a deep_shortcut_container.xml, mas SEM
     android:background (nenhuma cor própria - o fundo visível é o do
     retângulo único xaulinxs_app_popup_sheet_background, atrás de
     tudo) e SEM elevação (não é mais um bloco flutuante próprio).
     showDividers desenha uma linha fina (xaulinxs_app_popup_row_divider)
     entre cada barra, no lugar da antiga separação por sombra/canto
     arredondado entre balões.
-->
<LinearLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:id="@+id/deep_shortcuts_container"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:tag="@string/popup_container_iterate_children"
    android:orientation="vertical"
    android:divider="@drawable/xaulinxs_app_popup_row_divider"
    android:showDividers="middle"
    android:dividerPadding="@dimen/xaulinxs_option_row_padding" />
""",
    "res/layout/xaulinxs_app_popup_system_shortcut_container.xml": """<?xml version="1.0" encoding="utf-8"?>
<!--
     XaulinXs Customizations - Fase 3 (Balões -> Barras).
     Equivalente a system_shortcut_rows_container.xml, mas SEM
     android:background e SEM elevação - mesmo raciocínio de
     xaulinxs_app_popup_deep_shortcut_container.xml.
-->
<LinearLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:id="@+id/system_shortcuts_container"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:tag="@string/popup_container_iterate_children"
    android:orientation="vertical"
    android:divider="@drawable/xaulinxs_app_popup_row_divider"
    android:showDividers="middle"
    android:dividerPadding="@dimen/xaulinxs_option_row_padding" />
""",
    "res/layout/xaulinxs_app_popup_system_shortcut_icons_container.xml": """<?xml version="1.0" encoding="utf-8"?>
<!--
     XaulinXs Customizations - Fase 3 (Balões -> Barras).
     Equivalente a system_shortcut_icons_container.xml (modo colapsado
     "ícones-apenas", usado quando o app tem mais de
     SHORTCUT_COLLAPSE_THRESHOLD = 6 atalhos+opções no total), mas SEM
     android:background e SEM elevação - mesmo raciocínio dos outros
     containers desta fase. Os ícones individuais
     (system_shortcut_icon_only/_start/_end, reaproveitados sem
     alteração) já não tinham fundo sólido próprio, só ripple via
     PopupItemIconOnly - por isso não precisaram de layout novo.
-->
<LinearLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:id="@+id/system_shortcuts_container"
    android:tag="@string/popup_container_iterate_children"
    android:layout_width="match_parent"
    android:layout_height="@dimen/system_shortcut_header_height"
    android:orientation="horizontal"
    android:gravity="end|center_vertical" />
""",
}

NEW_HEADER_CONTENT = """<?xml version="1.0" encoding="utf-8"?>
<!--
     XaulinXs Customizations (novo popup de app).

     Cabeçalho inserido como PRIMEIRO filho do popup de app (mesmo
     popup usado na área de trabalho, na hotseat e no menu de
     aplicativos - PopupControllerForAppIcon é o ponto único dos três).
     Os atalhos/apps existentes (system shortcuts + deep shortcuts)
     continuam sendo adicionados normalmente pelo código original
     logo abaixo deste cabeçalho.

     - Ícone grande no meio: clicável, abre o seletor de imagem/galeria
       (AppIconPickerActivity) pra trocar por uma imagem própria.
     - Nome do app num retângulo contornado: EditText editável de
       verdade - salva a renomeação ao perder o foco ou apertar
       "concluído" no teclado.
     - Interruptor "esconder do menu de aplicativos": persiste a
       escolha e filtra a lista de apps (AlphabeticalAppsList).

     XaulinXs Customizations - Fase 3: o interruptor era um
     androidx.appcompat.widget.SwitchCompat sem nenhum switchStyle do
     AppCompat disponível no tema deste popup (o tema do app só define
     android:switchStyle para o Switch NATIVO, usado pelas
     Configurações - ver res/values/styles.xml, SwitchStyle) - por isso
     desenhava sem trilho/thumb, parecendo "só um retângulo que não faz
     nada" mesmo com o listener de clique funcionando por trás. Trocado
     para android.widget.Switch com o MESMO estilo usado nas
     Configurações (style="@style/SwitchStyle"), aplicado direto na
     view em vez de depender do tema herdado - fica visualmente
     idêntico ao interruptor de "Esconder da gaveta de aplicativos" já
     usado no editor de ícone do Lawnchair/Configurações.

     Largura trocada de xaulinxs_app_popup_width (280dp) para
     xaulinxs_app_popup_sheet_width (320dp) - mesma largura agora usada
     pelas barras de atalhos/opções abaixo dele, unificando o retângulo
     inteiro numa única largura (antes o cabeçalho e os itens tinham
     larguras diferentes, uma das causas do popup parecer "bagunçado").
-->
<LinearLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:id="@+id/xaulinxs_app_popup_header"
    android:layout_width="@dimen/xaulinxs_app_popup_sheet_width"
    android:layout_height="wrap_content"
    android:orientation="vertical"
    android:gravity="center_horizontal"
    android:paddingTop="@dimen/xaulinxs_option_row_padding"
    android:paddingStart="@dimen/xaulinxs_option_row_padding"
    android:paddingEnd="@dimen/xaulinxs_option_row_padding"
    android:paddingBottom="@dimen/xaulinxs_option_row_padding">

    <ImageView
        android:id="@+id/xaulinxs_app_popup_icon"
        android:layout_width="@dimen/xaulinxs_app_popup_icon_size"
        android:layout_height="@dimen/xaulinxs_app_popup_icon_size"
        android:background="@drawable/xaulinxs_app_popup_icon_bg"
        android:padding="@dimen/xaulinxs_option_stroke_width"
        android:contentDescription="@string/xaulinxs_app_popup_icon_desc"
        android:scaleType="fitCenter" />

    <EditText
        android:id="@+id/xaulinxs_app_popup_name"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginTop="@dimen/xaulinxs_option_row_padding"
        android:background="@drawable/xaulinxs_app_popup_field_bg"
        android:paddingTop="@dimen/xaulinxs_option_stroke_padding"
        android:paddingBottom="@dimen/xaulinxs_option_stroke_padding"
        android:paddingStart="@dimen/xaulinxs_option_row_padding"
        android:paddingEnd="@dimen/xaulinxs_option_row_padding"
        android:gravity="center"
        android:singleLine="true"
        android:ellipsize="end"
        android:textSize="16sp"
        android:textColor="?attr/popupTextColor"
        android:textColorHint="?attr/popupTextColor"
        android:importantForAutofill="no"
        android:inputType="text"
        android:imeOptions="actionDone" />

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginTop="@dimen/xaulinxs_option_row_padding"
        android:background="@drawable/xaulinxs_app_popup_field_bg"
        android:orientation="horizontal"
        android:gravity="center_vertical"
        android:paddingStart="@dimen/xaulinxs_option_row_padding"
        android:paddingEnd="@dimen/xaulinxs_option_stroke_padding"
        android:paddingTop="@dimen/xaulinxs_option_stroke_padding"
        android:paddingBottom="@dimen/xaulinxs_option_stroke_padding"
        android:minHeight="@dimen/xaulinxs_option_row_height">

        <TextView
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="@string/xaulinxs_app_popup_hide_label"
            android:textSize="14sp"
            android:textColor="?attr/popupTextColor" />

        <Switch
            android:id="@+id/xaulinxs_app_popup_hide_switch"
            style="@style/SwitchStyle"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:checked="false"
            android:text=""
            android:textOn=""
            android:textOff="" />

    </LinearLayout>

</LinearLayout>
"""

DIMENS_SNIPPET = """    <!-- Fase 3: retângulo único do popup de app (fundo real conectado à
         cor manual dos balões + largura unificada com o cabeçalho). -->
    <dimen name="xaulinxs_app_popup_sheet_width">320dp</dimen>
    <dimen name="xaulinxs_app_popup_sheet_corner_radius">28dp</dimen>
"""

POPUP_DIMENS_REL_PATH = "res/values/xaulinxs_popup_dimens.xml"
CONTAINER_KT_REL_PATH = "src/com/android/launcher3/popup/PopupContainerWithArrow.kt"
HEADER_XML_REL_PATH = "res/layout/xaulinxs_app_popup_header.xml"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_new_file(repo: Path, rel_path: str, content: str) -> str:
    """Cria o arquivo se nao existir. Se existir com conteudo diferente do
    esperado (nem o antigo, nem o novo), aborta sem sobrescrever."""
    path = repo / rel_path
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if current == content:
            return "skip (ja aplicado)"
        raise SystemExit(
            f"CONFLITO: {rel_path} ja existe com conteudo diferente do "
            f"esperado por este script. Abortando para nao sobrescrever "
            f"nada manualmente editado."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return "criado"


def patch_header(repo: Path) -> str:
    path = repo / HEADER_XML_REL_PATH
    if not path.exists():
        raise SystemExit(f"ERRO: {HEADER_XML_REL_PATH} nao encontrado.")
    current = path.read_text(encoding="utf-8")
    if current == NEW_HEADER_CONTENT:
        return "skip (ja aplicado)"
    if "androidx.appcompat.widget.SwitchCompat" not in current:
        raise SystemExit(
            f"CONFLITO: {HEADER_XML_REL_PATH} nao esta no estado original "
            f"esperado (SwitchCompat) nem no estado novo esperado. "
            f"Abortando para nao sobrescrever edicao manual."
        )
    path.write_text(NEW_HEADER_CONTENT, encoding="utf-8")
    return "atualizado (SwitchCompat -> Switch nativo com SwitchStyle)"


def patch_dimens(repo: Path) -> str:
    path = repo / POPUP_DIMENS_REL_PATH
    if not path.exists():
        raise SystemExit(f"ERRO: {POPUP_DIMENS_REL_PATH} nao encontrado.")
    current = path.read_text(encoding="utf-8")
    if "xaulinxs_app_popup_sheet_width" in current:
        return "skip (ja aplicado)"
    if "</resources>" not in current:
        raise SystemExit(
            f"CONFLITO: {POPUP_DIMENS_REL_PATH} nao tem a tag "
            f"</resources> esperada. Abortando."
        )
    new_content = current.replace("</resources>", DIMENS_SNIPPET + "</resources>")
    path.write_text(new_content, encoding="utf-8")
    return "atualizado (+ xaulinxs_app_popup_sheet_width/corner_radius)"


def patch_container_kotlin(repo: Path) -> str:
    """
    Edita PopupContainerWithArrow.kt para:
      - trocar os layouts dos containers/itens (deep_shortcut/system_shortcut)
        pelas novas versoes em barra, so dentro deste arquivo.
      - dar largura fixa (xaulinxs_app_popup_sheet_width) ao container raiz
        do popup em vez de WRAP_CONTENT puro (o wrap_content de LayoutParams
        continua valendo pra ALTURA - so a largura passa a ser fixa e
        dinamica o suficiente pra caber o conteudo, igual um popup normal
        do Android).
      - aplicar o fundo do retangulo (xaulinxs_app_popup_sheet_background)
        + a extracao de cor da feature de cor manual dos baloes
        (XaulinXsBalloonColor), reaplicada tambem quando a preferencia de
        cor mudar (mesmo padrao ja usado por XaulinXsOptionsSheet).
    """
    path = repo / CONTAINER_KT_REL_PATH
    if not path.exists():
        raise SystemExit(f"ERRO: {CONTAINER_KT_REL_PATH} nao encontrado.")
    content = path.read_text(encoding="utf-8")

    changed = False
    marker = "// XaulinXs Customizations - Fase 3 (popup de app: retângulo real)"
    if marker in content:
        return "skip (ja aplicado)"

    # 0) Override critico: ArrowPopup.assignMarginsAndBackgrounds() (chamado
    #    por show()) reatribui o FUNDO de cada DeepShortcutView visivel via
    #    isShortcutOrWrapper() - inclusive setBackgroundResource(single_item_primary)
    #    quando so ha 1 atalho visivel - o que sobrescreveria de volta o
    #    fundo transparente das novas barras (xaulinxs_app_popup_row_bg).
    #    Sem este override, o problema 1 (balao em vez de barra) voltaria
    #    a acontecer especificamente no caso de 1 unico atalho.
    old_should_add_arrow = (
        "    // XaulinXs Customizations - Fase 1: o popup de app deixou de ser um balão com seta\n"
        "    // apontando pro ícone - agora é um retângulo grande e contornado, então a seta não\n"
        "    // faz mais sentido visualmente.\n"
        "    override fun shouldAddArrow(): Boolean {\n"
        "        return false\n"
        "    }\n"
    )
    new_should_add_arrow = (
        old_should_add_arrow
        + "\n"
        + f"    {marker}: assignMarginsAndBackgrounds()\n"
        "    // (chamado por show()) reatribuiria o fundo de cada barra (inclusive\n"
        "    // single_item_primary quando só há 1 atalho visível), desfazendo o fundo\n"
        "    // transparente das novas barras (xaulinxs_app_popup_row_bg) - o retângulo\n"
        "    // único (xaulinxs_app_popup_sheet_background) já é o único fundo visível\n"
        "    // agora, então nenhuma DeepShortcutView deve mais ganhar fundo próprio.\n"
        "    override fun isShortcutOrWrapper(view: View): Boolean {\n"
        "        return false\n"
        "    }\n"
    )
    if old_should_add_arrow not in content:
        raise SystemExit(
            f"CONFLITO: bloco shouldAddArrow() não está no formato esperado "
            f"em {CONTAINER_KT_REL_PATH}. Abortando."
        )
    content = content.replace(old_should_add_arrow, new_should_add_arrow, 1)

    # 1) Import da feature de cor manual dos baloes.
    old_import = (
        "import com.xaulinxs.customizations.apps.XaulinXsAppOverrides\n"
    )
    new_import = (
        "import com.xaulinxs.customizations.apps.XaulinXsAppOverrides\n"
        "import com.xaulinxs.customizations.theme.XaulinXsBalloonColor\n"
        "import android.graphics.drawable.GradientDrawable\n"
    )
    if old_import not in content:
        raise SystemExit(
            f"CONFLITO: import de XaulinXsAppOverrides nao encontrado em "
            f"{CONTAINER_KT_REL_PATH} no formato esperado. Abortando."
        )
    content = content.replace(old_import, new_import, 1)
    changed = True

    # 2) Trocar os 4 layouts originais (balao) pelos 4 novos (barra) em
    #    todos os pontos onde sao referenciados dentro deste arquivo.
    #    Word boundary (\b) evita que "system_shortcut_rows_container"
    #    seja tocado pela troca de "system_shortcut" e vice-versa (uma
    #    substring do nome do outro).
    layout_swaps = [
        (r"R\.layout\.system_shortcut_rows_container\b",
         "R.layout.xaulinxs_app_popup_system_shortcut_container"),
        (r"R\.layout\.system_shortcut_icons_container\b",
         "R.layout.xaulinxs_app_popup_system_shortcut_icons_container"),
        (r"R\.layout\.system_shortcut\b(?!_)",
         "R.layout.xaulinxs_app_popup_system_shortcut"),
        (r"R\.layout\.deep_shortcut_container\b",
         "R.layout.xaulinxs_app_popup_deep_shortcut_container"),
        (r"R\.layout\.deep_shortcut\b(?!_)",
         "R.layout.xaulinxs_app_popup_deep_shortcut"),
    ]
    for pattern, replacement in layout_swaps:
        new_content, count = re.subn(pattern, replacement, content)
        if count == 0:
            raise SystemExit(
                f"CONFLITO: referencia ao padrao '{pattern}' nao encontrada "
                f"em {CONTAINER_KT_REL_PATH}. Abortando."
            )
        content = new_content

    # 2.1) containerWidth (o valor que cada barra usa como largura -
    #      v.layoutParams.width = containerWidth) partia de
    #      R.dimen.bg_popup_item_width (216dp) - MENOR que a nova largura
    #      do retângulo (xaulinxs_app_popup_sheet_width, 320dp). Sem esta
    #      troca, as barras ficariam mais estreitas que o próprio
    #      retângulo, sobrando espaço vazio dos dois lados dentro dele -
    #      "tamanho dinâmico" teria virado "retângulo maior com barras
    #      pequenas soltas lá dentro", o mesmo problema 1 de outra forma.
    old_width_dimen = "R.dimen.bg_popup_item_width"
    new_width_dimen = "R.dimen.xaulinxs_app_popup_sheet_width"
    width_count = content.count(old_width_dimen)
    if width_count == 0:
        raise SystemExit(
            f"CONFLITO: referencia a '{old_width_dimen}' nao encontrada em "
            f"{CONTAINER_KT_REL_PATH}. Abortando."
        )
    content = content.replace(old_width_dimen, new_width_dimen)

    # 3) Largura fixa do container raiz (era WRAP_CONTENT) + fundo do
    #    retangulo aplicado logo apos a criacao do container, junto do
    #    cabeçalho ja existente.
    old_create_block = (
        "            container.layoutParams =\n"
        "                LayoutParams(\n"
        "                    ViewGroup.LayoutParams.WRAP_CONTENT,\n"
        "                    ViewGroup.LayoutParams.WRAP_CONTENT,\n"
        "                )\n"
        "            // XaulinXs Customizations - Fase 1: cabeçalho novo (ícone grande, nome, interruptor\n"
        "            // de esconder do menu de aplicativos) como primeiro filho do popup. Os atalhos do\n"
        "            // app (deep shortcuts / system shortcuts) continuam sendo adicionados depois disso,\n"
        "            // pelo código original, sem nenhuma mudança de comportamento.\n"
        "            bindXaulinXsAppPopupHeader(container, itemInfo)\n"
        "            return container\n"
    )
    new_create_block = (
        "            container.layoutParams =\n"
        "                LayoutParams(\n"
        "                    ViewGroup.LayoutParams.WRAP_CONTENT,\n"
        "                    ViewGroup.LayoutParams.WRAP_CONTENT,\n"
        "                )\n"
        "            // XaulinXs Customizations - Fase 1: cabeçalho novo (ícone grande, nome, interruptor\n"
        "            // de esconder do menu de aplicativos) como primeiro filho do popup. Os atalhos do\n"
        "            // app (deep shortcuts / system shortcuts) continuam sendo adicionados depois disso,\n"
        "            // pelo código original, sem nenhuma mudança de comportamento.\n"
        "            bindXaulinXsAppPopupHeader(container, itemInfo)\n"
        f"            {marker}: o balão de seta virou um retângulo real -\n"
        "            // fundo próprio (não mais herdado do container pai) + cor conectada à\n"
        "            // mesma feature de cor manual/extração de wallpaper que já pinta os\n"
        "            // itens individuais (XaulinXsBalloonColor, ver ArrowPopup.java mColors).\n"
        "            container.applyXaulinXsSheetBackground()\n"
        "            return container\n"
    )
    if old_create_block not in content:
        raise SystemExit(
            f"CONFLITO: bloco de criação do container (create()) não está "
            f"no formato esperado em {CONTAINER_KT_REL_PATH}. Abortando."
        )
    content = content.replace(old_create_block, new_create_block, 1)

    # 4) Metodo de instancia que aplica a cor (reaproveitavel: chamado na
    #    criacao e, futuramente, se a preferencia mudar em runtime).
    old_bind_header_start = (
        "        /**\n"
        "         * Infla o cabeçalho [R.layout.xaulinxs_app_popup_header] como primeiro filho do popup e\n"
    )
    new_bind_header_start = (
        "        /**\n"
        "         * Define o fundo do retângulo do popup\n"
        "         * ([R.drawable.xaulinxs_app_popup_sheet_background]) e, em seguida, aplica em\n"
        "         * cima dele a mesma cor que [XaulinXsBalloonColor] já usa para os itens\n"
        "         * individuais - override manual (se ligado) ou extração do wallpaper; se\n"
        "         * nenhuma das duas estiver disponível, mantém a cor estática original do\n"
        "         * drawable (materialColorSurfaceContainer), sem quebrar nada.\n"
        "         */\n"
        "        private fun PopupContainerWithArrow<*>.applyXaulinXsSheetBackground() {\n"
        "            val sheetBackground =\n"
        "                context.getDrawable(R.drawable.xaulinxs_app_popup_sheet_background)\n"
        "                    ?.mutate()\n"
        "            background = sheetBackground\n"
        "            val overrideColor =\n"
        "                XaulinXsBalloonColor.getBalloonColorOverride(context) ?: return\n"
        "            if (sheetBackground is GradientDrawable) {\n"
        "                sheetBackground.setColor(overrideColor)\n"
        "            }\n"
        "        }\n"
        "\n"
        "        /**\n"
        "         * Infla o cabeçalho [R.layout.xaulinxs_app_popup_header] como primeiro filho do popup e\n"
    )
    if old_bind_header_start not in content:
        raise SystemExit(
            f"CONFLITO: assinatura de bindXaulinXsAppPopupHeader não "
            f"encontrada no formato esperado em {CONTAINER_KT_REL_PATH}. "
            f"Abortando."
        )
    content = content.replace(old_bind_header_start, new_bind_header_start, 1)

    path.write_text(content, encoding="utf-8")
    return "atualizado (layouts em barra + largura fixa + cor do retângulo)"


def main() -> None:
    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    if not (repo / "src" / "com" / "android" / "launcher3").exists():
        raise SystemExit(
            f"ERRO: {repo} não parece ser a raiz do repo XaulinXsLauncher3 "
            f"(src/com/android/launcher3 não encontrado)."
        )

    print(f"Repo: {repo}\n")

    for rel_path, content in FILES_TO_CREATE.items():
        status = write_new_file(repo, rel_path, content)
        print(f"[{status}] {rel_path}")

    status = patch_dimens(repo)
    print(f"[{status}] {POPUP_DIMENS_REL_PATH}")

    status = patch_header(repo)
    print(f"[{status}] {HEADER_XML_REL_PATH}")

    status = patch_container_kotlin(repo)
    print(f"[{status}] {CONTAINER_KT_REL_PATH}")

    print(
        "\nConcluído. Lembrete: builde com "
        "'./gradlew assembleNoQuickstepDebug' (nunca assembleDebug "
        "genérico) e dê 'git push' depois de confirmar que funcionou."
    )


if __name__ == "__main__":
    main()
