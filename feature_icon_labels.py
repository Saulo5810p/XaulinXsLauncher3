#!/usr/bin/env python3
"""
Feature: Mostrar/ocultar labels dos ícones.

IMPORTANTE — investigação antes de codar (pedida no HANDOFF):
O AOSP já tem um mecanismo nativo pra isso: LauncherPrefs.WORKSPACE_ITEMS_LABEL_HIDDEN
+ DeviceProfile.Builder.setIsWorkspaceItemsLabelHidden() + a lógica em
WorkspaceProfile.kt que zera iconTextSizePx/iconDrawablePaddingPx. MAS esse
mecanismo:
  1) só existe no caminho de "grid responsivo" (createWorkspaceProfileResponsiveGrid) —
     o grid padrão de celular (Large Phone / 5_by_5, 4_by_4 etc. no
     device_profiles.xml) usa o caminho NÃO responsivo, que nem recebe esse
     parâmetro. Só o grid especial "fixed_landscape_mode" é responsivo.
  2) está atrás de com.android.systemui.shared.Flags.workspaceItemsLabelHidden(),
     e o stub usado neste build (aosp-stubs/.../Flags.java) retorna sempre
     `false` — hardcoded, igual às outras armadilhas do device_profiles/flags
     já catalogadas no HANDOFF.
Ou seja: reaproveitar esse mecanismo "nativo" seria um beco sem saída igual o
`@android:color/system_*` (não funciona no grid real do celular). Por isso
este script NÃO mexe em DeviceProfile/InvariantDeviceProfile/WorkspaceProfile.

Caminho escolhido: BubbleTextView.applyLabel() é o único ponto do AOSP onde
TODO label de ícone é setado (home, hotseat, pasta, app drawer — todos usam
BubbleTextView). Hookar ali funciona independente do tipo de grid, sem tocar
em nenhum cálculo de layout/célula. Trade-off: só o TEXTO some — o espaço que
o label ocuparia continua reservado (não recalcula cellHeight). Se quiser a
versão que também reduz o espaço, isso me exigiria entrar no mesmo território
arriscado do item 1 acima.

O que este script faz:
1. Cria modules/customizations/.../icons/XaulinXsIconLabels.kt (novo) — guarda
   o toggle via LauncherPrefs.
2. Cria modules/customizations/.../settings/IconLabelsPreference.kt (novo) —
   SwitchPreference que persiste o valor e força um reload do modelo (rebind
   de todos os ícones já na tela) via LauncherModel.forceReload().
3. Edita BubbleTextView.java (AOSP) — 1 linha cirúrgica em applyLabel(): troca
   o texto por "" quando o toggle estiver ativo. contentDescription (usado por
   leitores de tela) continua sendo setado normalmente — só o texto visível
   some.
4. Edita res/xml/launcher_preferences.xml — adiciona o switch na tela
   "XaulinXs Customizations" já existente (ancorado no fechamento do bloco,
   não depende de quais outras features você já aplicou antes).
5. Edita res/values/xaulinxs_strings.xml — título/resumo do switch.

Idempotente. Rode a partir da RAIZ do repositório:
    python3 feature_icon_labels.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

ICON_LABELS_KT = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/icons/XaulinXsIconLabels.kt"
ICON_LABELS_PREF_KT = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/settings/IconLabelsPreference.kt"
BUBBLE_TEXT_VIEW = REPO_ROOT / "src/com/android/launcher3/BubbleTextView.java"
PREFS_XML = REPO_ROOT / "res/xml/launcher_preferences.xml"
STRINGS_XML = REPO_ROOT / "res/values/xaulinxs_strings.xml"


def fail(msg: str):
    print(f"[ERRO] {msg}")
    sys.exit(1)


def require_parent(path: Path):
    if not path.parent.exists():
        fail(
            f"Diretório não encontrado: {path.parent}\n"
            "Confirme que está rodando este script a partir da raiz do repositório."
        )


def require_file(path: Path):
    if not path.exists():
        fail(
            f"Arquivo não encontrado: {path}\n"
            "Confirme que está rodando este script a partir da raiz do repositório "
            "e que o repo está no estado esperado pelo HANDOFF."
        )


def apply_replace(path: Path, old: str, new: str, step_name: str):
    text = path.read_text(encoding="utf-8")
    if old not in text:
        fail(
            f"[{step_name}] Âncora esperada não encontrada em {path}.\n"
            "O arquivo pode ter mudado desde o HANDOFF. Cole o conteúdo atual "
            "do arquivo para eu regenerar o patch."
        )
    count = text.count(old)
    if count != 1:
        fail(f"[{step_name}] Âncora encontrada {count} vezes em {path}, esperava 1. Abortando por segurança.")
    path.write_text(text.replace(old, new), encoding="utf-8")
    print(f"[OK] {step_name} aplicado em {path.relative_to(REPO_ROOT)}")


def step_create_icon_labels_kt():
    require_parent(ICON_LABELS_KT)
    if ICON_LABELS_KT.exists() and "isHidden" in ICON_LABELS_KT.read_text(encoding="utf-8"):
        print(f"[SKIP] {ICON_LABELS_KT.relative_to(REPO_ROOT)} já existe.")
        return
    content = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Guarda e lê o toggle de "ocultar labels dos ícones". Lido diretamente por
 * BubbleTextView.applyLabel() (edição cirúrgica em BubbleTextView.java) —
 * funciona pra qualquer BubbleTextView (home, hotseat, pasta, app drawer),
 * já que é o ponto único onde todo label de ícone é setado no AOSP.
 *
 * Não reaproveita LauncherPrefs.WORKSPACE_ITEMS_LABEL_HIDDEN (mecanismo
 * nativo do AOSP) de propósito: esse mecanismo só funciona no grid
 * responsivo, que este device não usa (ver comentário no topo do script
 * feature_icon_labels.py).
 */
package com.xaulinxs.customizations.icons

import android.content.Context
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

object XaulinXsIconLabels {
    private const val KEY_LABELS_HIDDEN = "xaulinxs_icon_labels_hidden"

    @JvmField
    val LABELS_HIDDEN = backedUpItem(KEY_LABELS_HIDDEN, false)

    @JvmStatic
    fun isHidden(context: Context): Boolean = LauncherPrefs.get(context).get(LABELS_HIDDEN)
}
'''
    ICON_LABELS_KT.write_text(content, encoding="utf-8")
    print(f"[OK] Criado {ICON_LABELS_KT.relative_to(REPO_ROOT)}")


def step_create_icon_labels_preference_kt():
    require_parent(ICON_LABELS_PREF_KT)
    if ICON_LABELS_PREF_KT.exists() and "IconLabelsPreference" in ICON_LABELS_PREF_KT.read_text(encoding="utf-8"):
        print(f"[SKIP] {ICON_LABELS_PREF_KT.relative_to(REPO_ROOT)} já existe.")
        return
    content = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherAppState
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.icons.XaulinXsIconLabels.LABELS_HIDDEN

class IconLabelsPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(LABELS_HIDDEN)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(LABELS_HIDDEN, newValue as Boolean)
            // XaulinXs Customizations: força o rebind de todos os ícones (home,
            // hotseat, pastas, app drawer) pra aplicar/remover os labels na hora.
            LauncherAppState.getInstance(context).model.forceReload("xaulinxs_icon_labels_toggle")
            true
        }
    }
}
'''
    ICON_LABELS_PREF_KT.write_text(content, encoding="utf-8")
    print(f"[OK] Criado {ICON_LABELS_PREF_KT.relative_to(REPO_ROOT)}")


def step_patch_bubble_text_view():
    require_file(BUBBLE_TEXT_VIEW)
    text = BUBBLE_TEXT_VIEW.read_text(encoding="utf-8")
    if "XaulinXsIconLabels" in text:
        print(f"[SKIP] {BUBBLE_TEXT_VIEW.relative_to(REPO_ROOT)} já tem o hook do XaulinXsIconLabels.")
        return
    old = (
        "            if (isTextWithArchivingIcon) {\n"
        "                setTextWithArchivingIcon(label);\n"
        "            } else {\n"
        "                setText(label);\n"
        "            }\n"
    )
    new = (
        "            if (isTextWithArchivingIcon) {\n"
        "                setTextWithArchivingIcon(label);\n"
        "            } else {\n"
        "                // XaulinXs Customizations: oculta o texto visível quando o toggle\n"
        "                // \"ocultar labels dos ícones\" está ativo (contentDescription abaixo\n"
        "                // continua normal, pra não quebrar leitor de tela).\n"
        "                setText(com.xaulinxs.customizations.icons.XaulinXsIconLabels.isHidden(getContext())\n"
        "                        ? \"\" : label);\n"
        "            }\n"
    )
    apply_replace(BUBBLE_TEXT_VIEW, old, new, "BubbleTextView.java: hook em applyLabel()")


def step_patch_prefs_xml():
    require_file(PREFS_XML)
    text = PREFS_XML.read_text(encoding="utf-8")
    if "IconLabelsPreference" in text:
        print(f"[SKIP] {PREFS_XML.relative_to(REPO_ROOT)} já tem IconLabelsPreference.")
        return
    old = (
        "    </PreferenceScreen>\n"
        "    <!-- ============ XaulinXs Customizations — fim ============ -->\n"
    )
    new = (
        "        <com.xaulinxs.customizations.settings.IconLabelsPreference\n"
        "            android:key=\"xaulinxs_icon_labels_hidden\"\n"
        "            android:title=\"@string/xaulinxs_icon_labels_title\"\n"
        "            android:summary=\"@string/xaulinxs_icon_labels_summary\"\n"
        "            android:persistent=\"false\" />\n"
        "\n"
    ) + old
    apply_replace(PREFS_XML, old, new, "launcher_preferences.xml: switch de labels")


def step_patch_strings_xml():
    require_file(STRINGS_XML)
    text = STRINGS_XML.read_text(encoding="utf-8")
    if "xaulinxs_icon_labels_title" in text:
        print(f"[SKIP] {STRINGS_XML.relative_to(REPO_ROOT)} já tem as strings do switch.")
        return
    content = text.rstrip("\n")
    if not content.endswith("</resources>"):
        fail(f"{STRINGS_XML} não termina com </resources> como esperado — cole o conteúdo atual pra eu ajustar.")
    body = content[: -len("</resources>")]
    new_content = (
        body
        + '    <string name="xaulinxs_icon_labels_title">Ocultar labels dos ícones</string>\n'
        + '    <string name="xaulinxs_icon_labels_summary">Esconde o texto abaixo dos ícones na tela inicial, gaveta de apps e pastas</string>\n'
        + "</resources>\n"
    )
    STRINGS_XML.write_text(new_content, encoding="utf-8")
    print(f"[OK] {STRINGS_XML.relative_to(REPO_ROOT)}: strings do switch adicionadas")


def main():
    print("== Feature: mostrar/ocultar labels dos ícones ==")
    step_create_icon_labels_kt()
    step_create_icon_labels_preference_kt()
    step_patch_bubble_text_view()
    step_patch_prefs_xml()
    step_patch_strings_xml()
    print("\nConcluído. Recompile com:")
    print("  ./gradlew assembleNoQuickstepDebug --stacktrace 2>&1 | tee build_nextNN.log")


if __name__ == "__main__":
    main()
