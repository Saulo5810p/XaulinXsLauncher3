#!/usr/bin/env python3
"""
XaulinXs Customizations - Fase 4 do popup de app.

Dá aos itens soltos do popup (Informações do app, Widgets, Remover,
Configurar barra de busca, atalhos de apps) o mesmo tratamento visual
de retângulo com fundo que já existe no cabeçalho (campo de nome +
interruptor "esconder do menu de aplicativos"): fundo
?attr/popupColorPrimary + contorno ?attr/popupColorTertiary + cantos
arredondados.

Antes, esses itens usavam xaulinxs_app_popup_row_bg totalmente
transparente (só ripple) - a cor visível vinha só do retângulo único
atrás de tudo (xaulinxs_app_popup_sheet_background), sem feedback de
toque visível e destoando do cabeçalho.

NÃO mexe em nenhuma flag do Flags.java (expandableLongPressMenu,
enableLauncherIconShapes, enableExpressiveFolderExpansion) - o stub já
está com as 3 em `false` no repositório remoto, ou seja, o painel
Compose feio nunca foi publicado. Esta é uma correção puramente visual
no popup ArrowPopup/PopupContainerWithArrow original, que continua
sendo o único popup de item usado no projeto.

Uso:
    python3 apply_popup_item_rectangles.py /caminho/para/XaulinXsLauncher3

Idempotente: rodar de novo não duplica nada (cada write verifica o
conteúdo atual antes de decidir sobrescrever/pular/abortar).
"""

import sys
import pathlib

MARKER_ROW_BG = "XaulinXs Customizations - Fase 4 (retângulo próprio por item)"
MARKER_ROW_GAP = "XaulinXs Customizations - Fase 4."
MARKER_DEEP_CONTAINER = "Fase 4: cada item (xaulinxs_app_popup_row_bg) agora tem contorno"
MARKER_SYS_CONTAINER = "Fase 4: mesma troca de divider por gap vazio"
MARKER_DIMENS = "xaulinxs_app_popup_row_radius"

ROW_BG_CONTENT = '''<?xml version="1.0" encoding="utf-8"?>
<!--
     XaulinXs Customizations - Fase 4 (retângulo próprio por item).
     Usado nas linhas de atalho (deep shortcuts) e nas linhas de opção
     do sistema (Widgets/Adicionar à tela inicial/Informações do app/
     Remover/Configurar barra de busca).
     Antes (Fase 3) era transparente - a cor visível vinha só do
     retângulo único por trás (xaulinxs_app_popup_sheet_background),
     sem feedback de toque visível e sem o mesmo peso visual do
     cabeçalho. Agora usa o MESMO padrão do campo de nome/interruptor
     do cabeçalho (xaulinxs_app_popup_field_bg): fundo
     ?attr/popupColorPrimary + contorno ?attr/popupColorTertiary,
     cantos arredondados menores (xaulinxs_app_popup_row_radius) pra
     diferenciar levemente do raio maior do cabeçalho sem destoar.
     O ripple continua por cima como state, então o feedback de toque
     não se perde.
-->
<ripple xmlns:android="http://schemas.android.com/apk/res/android"
    android:color="?android:attr/colorControlHighlight">
    <item>
        <shape android:shape="rectangle">
            <solid android:color="?attr/popupColorPrimary"/>
            <stroke
                android:width="@dimen/xaulinxs_option_stroke_width"
                android:color="?attr/popupColorTertiary"/>
            <corners android:radius="@dimen/xaulinxs_app_popup_row_radius" />
        </shape>
    </item>
</ripple>
'''

ROW_GAP_CONTENT = '''<?xml version="1.0" encoding="utf-8"?>
<!--
     XaulinXs Customizations - Fase 4.
     Espaçador transparente usado como android:divider nos containers
     de shortcut/system-shortcut do popup de app, no lugar da antiga
     linha fina (xaulinxs_app_popup_row_divider). Agora que cada item
     (xaulinxs_app_popup_row_bg) tem seu próprio retângulo contornado,
     uma linha divisória ficaria colada nas bordas - isto aqui é só
     respiro vazio de altura fixa entre um retângulo e o próximo.
-->
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="rectangle">
    <solid android:color="@android:color/transparent"/>
    <size android:height="@dimen/xaulinxs_app_popup_row_gap" />
</shape>
'''

DEEP_CONTAINER_CONTENT = '''<?xml version="1.0" encoding="utf-8"?>
<!--
     XaulinXs Customizations - Fase 3 (Balões -> Barras).
     Equivalente a deep_shortcut_container.xml, mas SEM
     android:background (nenhuma cor própria - o fundo visível é o do
     retângulo único xaulinxs_app_popup_sheet_background, atrás de
     tudo) e SEM elevação (não é mais um bloco flutuante próprio).

     Fase 4: cada item (xaulinxs_app_popup_row_bg) agora tem contorno e
     fundo próprios, então a antiga linha fina divisória
     (xaulinxs_app_popup_row_divider) ficaria colada nas bordas dos
     retângulos - trocada por um espaço vazio real
     (xaulinxs_app_popup_row_gap) entre as barras.
-->
<LinearLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:id="@+id/deep_shortcuts_container"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:tag="@string/popup_container_iterate_children"
    android:orientation="vertical"
    android:divider="@drawable/xaulinxs_app_popup_row_gap"
    android:showDividers="middle" />
'''

SYS_CONTAINER_CONTENT = '''<?xml version="1.0" encoding="utf-8"?>
<!--
     XaulinXs Customizations - Fase 3 (Balões -> Barras).
     Equivalente a system_shortcut_rows_container.xml, mas SEM
     android:background e SEM elevação - mesmo raciocínio de
     xaulinxs_app_popup_deep_shortcut_container.xml.

     Fase 4: mesma troca de divider por gap vazio (ver comentário
     completo em xaulinxs_app_popup_deep_shortcut_container.xml).
-->
<LinearLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:id="@+id/system_shortcuts_container"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:tag="@string/popup_container_iterate_children"
    android:orientation="vertical"
    android:divider="@drawable/xaulinxs_app_popup_row_gap"
    android:showDividers="middle" />
'''

PRIOR_ROW_BG = '''<?xml version="1.0" encoding="utf-8"?>
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
'''

PRIOR_DEEP_CONTAINER = '''<?xml version="1.0" encoding="utf-8"?>
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
'''

PRIOR_SYS_CONTAINER = '''<?xml version="1.0" encoding="utf-8"?>
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
'''

DIMENS_ADDITION = '''    <!-- Fase 4: retângulo próprio por item (Informações do app, Widgets,
         Remover, Configurar barra de busca, atalhos). Raio um pouco menor
         que o do cabeçalho (xaulinxs_app_popup_field_radius, 20dp) pra
         manter hierarquia visual sem destoar. Gap substitui a antiga
         linha divisória fina, já que cada item agora tem contorno
         próprio - duas bordas coladas ficavam poluídas. -->
    <dimen name="xaulinxs_app_popup_row_radius">16dp</dimen>
    <dimen name="xaulinxs_app_popup_row_gap">8dp</dimen>
</resources>
'''


def write_if_needed(path: pathlib.Path, expected_content: str, marker: str,
                     label: str, known_prior_content: str | None = None) -> bool:
    """Escreve o arquivo se ainda não tem o marcador da Fase 4.

    Se o arquivo já existe e NÃO tem o marcador, só sobrescreve quando o
    conteúdo bate exatamente com o estado conhecido anterior (Fase 3 /
    recém-criado por este mesmo script). Qualquer outra coisa (edição
    manual do usuário, conflito real) aborta essa parte sem tocar no
    arquivo.
    """
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if marker in current:
            print(f"[SKIP] {label}: já aplicado (idempotente).")
            return True
        if known_prior_content is not None and current != known_prior_content:
            print(f"[ERRO] {label}: arquivo existe com conteúdo diferente do "
                  f"esperado (provável edição manual) — abortando esta parte "
                  f"sem sobrescrever. Aplique manualmente ou remova a "
                  f"customização antes de rodar de novo.")
            return False
    path.write_text(expected_content, encoding="utf-8")
    print(f"[OK]   {label}: aplicado.")
    return True


def append_dimens_if_needed(path: pathlib.Path) -> bool:
    if not path.exists():
        print(f"[ERRO] {path} não encontrado.")
        return False
    current = path.read_text(encoding="utf-8")
    if MARKER_DIMENS in current:
        print("[SKIP] xaulinxs_popup_dimens.xml: já aplicado (idempotente).")
        return True
    if "</resources>" not in current:
        print(f"[ERRO] {path}: não encontrei </resources> pra inserir antes.")
        return False
    new_content = current.replace(
        "    <dimen name=\"xaulinxs_app_popup_sheet_corner_radius\">28dp</dimen>\n</resources>",
        "    <dimen name=\"xaulinxs_app_popup_sheet_corner_radius\">28dp</dimen>\n" + DIMENS_ADDITION,
    )
    if new_content == current:
        print("[ERRO] xaulinxs_popup_dimens.xml: âncora de inserção não encontrada — "
              "arquivo pode ter sido editado manualmente. Abortando esta parte sem sobrescrever.")
        return False
    path.write_text(new_content, encoding="utf-8")
    print("[OK]   xaulinxs_popup_dimens.xml: dimens novas adicionadas.")
    return True


def main():
    if len(sys.argv) != 2:
        print("Uso: python3 apply_popup_item_rectangles.py /caminho/para/XaulinXsLauncher3")
        sys.exit(1)

    repo = pathlib.Path(sys.argv[1]).resolve()
    if not repo.is_dir():
        print(f"[ERRO] Diretório não encontrado: {repo}")
        sys.exit(1)

    ok = True

    ok &= write_if_needed(
        repo / "res/drawable/xaulinxs_app_popup_row_bg.xml",
        ROW_BG_CONTENT, MARKER_ROW_BG, "xaulinxs_app_popup_row_bg.xml",
        known_prior_content=PRIOR_ROW_BG,
    )
    ok &= write_if_needed(
        repo / "res/drawable/xaulinxs_app_popup_row_gap.xml",
        ROW_GAP_CONTENT, MARKER_ROW_GAP, "xaulinxs_app_popup_row_gap.xml (novo)",
        known_prior_content=None,  # arquivo novo, não existia antes
    )
    ok &= write_if_needed(
        repo / "res/layout/xaulinxs_app_popup_deep_shortcut_container.xml",
        DEEP_CONTAINER_CONTENT, MARKER_DEEP_CONTAINER, "xaulinxs_app_popup_deep_shortcut_container.xml",
        known_prior_content=PRIOR_DEEP_CONTAINER,
    )
    ok &= write_if_needed(
        repo / "res/layout/xaulinxs_app_popup_system_shortcut_container.xml",
        SYS_CONTAINER_CONTENT, MARKER_SYS_CONTAINER, "xaulinxs_app_popup_system_shortcut_container.xml",
        known_prior_content=PRIOR_SYS_CONTAINER,
    )
    ok &= append_dimens_if_needed(repo / "res/values/xaulinxs_popup_dimens.xml")

    if not ok:
        print("\n[FALHOU] Alguma parte não pôde ser aplicada — veja os [ERRO] acima. "
              "Nada foi sobrescrito às cegas.")
        sys.exit(1)

    print("\n[SUCESSO] Todos os itens do popup (Informações do app, Widgets, Remover, "
          "atalhos, Configurar barra de busca) agora usam o mesmo retângulo com fundo "
          "do cabeçalho. Rode assembleNoQuickstepDebug e compare visualmente com o "
          "cabeçalho.")


if __name__ == "__main__":
    main()
