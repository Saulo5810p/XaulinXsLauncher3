#!/usr/bin/env python3
"""
Feature: Transparência de ícones e do fundo do menu de apps (slider).

Dois sliders independentes, 0%-100%, default 100% (preserva o visual atual):

1) Opacidade dos ícones — hook único em BubbleTextView.applyCompoundDrawables()
   (mesmo método central que toda BubbleTextView usa pra aplicar o drawable
   do ícone — home, hotseat, pasta, app drawer), chamando icon.setAlpha().
   Ao mudar o slider, forçamos LauncherModel.forceReload() (mesmo mecanismo
   já usado na feature de labels) pra reaplicar nos ícones já na tela.

2) Opacidade do fundo (véu) do App Drawer — NÃO cria mecanismo novo: edita o
   WallpaperScrimHelper.kt que a feature de "fundo desfocado" já criou. Hoje
   ele usa um alpha fixo por tema (140 claro / 160 escuro); o slider vira um
   multiplicador percentual em cima desse alpha base, sem perder a diferença
   claro/escuro que já existia. Não precisa de nenhum "force reload": a cor
   do véu é recalculada toda vez que o App Drawer abre
   (AllAppsState.getWorkspaceScrimColor() já chama getScrimColor() do zero
   a cada transição), então o novo valor vale a partir da próxima abertura.

Nenhuma edição em arquivo AOSP desta vez além do hook único no BubbleTextView
(1 linha) — o resto é tudo dentro de com.xaulinxs.customizations.*, que já é
nosso.

O que este script faz:
1. Cria modules/customizations/.../icons/XaulinXsIconOpacity.kt (novo).
2. Cria modules/customizations/.../settings/IconOpacityPreference.kt (novo).
3. Cria modules/customizations/.../settings/ScrimOpacityPreference.kt (novo).
4. Edita modules/customizations/.../theme/WallpaperScrimHelper.kt (nosso) —
   adiciona o pref de opacidade do véu e aplica como multiplicador do alpha
   base.
5. Edita BubbleTextView.java (AOSP) — 1 linha cirúrgica em
   applyCompoundDrawables().
6. Edita res/xml/launcher_preferences.xml — adiciona os 2 sliders (ancorado
   no fechamento do bloco, não depende da ordem de outras features já
   aplicadas).
7. Edita res/values/xaulinxs_strings.xml — título/resumo dos 2 sliders.

Idempotente. Rode a partir da RAIZ do repositório:
    python3 feature_transparency.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

ICON_OPACITY_KT = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/icons/XaulinXsIconOpacity.kt"
ICON_OPACITY_PREF_KT = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/settings/IconOpacityPreference.kt"
SCRIM_OPACITY_PREF_KT = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/settings/ScrimOpacityPreference.kt"
SCRIM_HELPER_KT = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/theme/WallpaperScrimHelper.kt"
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
            "e que o repo está no estado esperado pelo HANDOFF (a feature de fundo "
            "desfocado do App Drawer, que cria WallpaperScrimHelper.kt, precisa já "
            "existir antes desta)."
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


def step_create_icon_opacity_kt():
    require_parent(ICON_OPACITY_KT)
    if ICON_OPACITY_KT.exists() and "getAlpha" in ICON_OPACITY_KT.read_text(encoding="utf-8"):
        print(f"[SKIP] {ICON_OPACITY_KT.relative_to(REPO_ROOT)} já existe.")
        return
    content = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Guarda e lê a opacidade dos ícones (0%-100%, 100% = opaco, igual ao
 * comportamento original). Lido diretamente por
 * BubbleTextView.applyCompoundDrawables() (edição cirúrgica em
 * BubbleTextView.java) — funciona pra qualquer BubbleTextView (home,
 * hotseat, pasta, app drawer), já que é o ponto único onde todo ícone é
 * aplicado no AOSP.
 */
package com.xaulinxs.customizations.icons

import android.content.Context
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

object XaulinXsIconOpacity {
    private const val KEY_ICON_OPACITY_PERCENT = "xaulinxs_icon_opacity_percent"
    const val MIN_PERCENT = 0
    const val MAX_PERCENT = 100

    @JvmField
    val ICON_OPACITY_PERCENT = backedUpItem(KEY_ICON_OPACITY_PERCENT, MAX_PERCENT)

    @JvmStatic
    fun getAlpha(context: Context): Int {
        val percent = LauncherPrefs.get(context).get(ICON_OPACITY_PERCENT).coerceIn(MIN_PERCENT, MAX_PERCENT)
        return Math.round(percent * 255f / 100f)
    }
}
'''
    ICON_OPACITY_KT.write_text(content, encoding="utf-8")
    print(f"[OK] Criado {ICON_OPACITY_KT.relative_to(REPO_ROOT)}")


def step_create_icon_opacity_preference_kt():
    require_parent(ICON_OPACITY_PREF_KT)
    if ICON_OPACITY_PREF_KT.exists() and "IconOpacityPreference" in ICON_OPACITY_PREF_KT.read_text(encoding="utf-8"):
        print(f"[SKIP] {ICON_OPACITY_PREF_KT.relative_to(REPO_ROOT)} já existe.")
        return
    content = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.LauncherAppState
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.icons.XaulinXsIconOpacity
import com.xaulinxs.customizations.icons.XaulinXsIconOpacity.ICON_OPACITY_PERCENT

class IconOpacityPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = XaulinXsIconOpacity.MIN_PERCENT
        max = XaulinXsIconOpacity.MAX_PERCENT
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(ICON_OPACITY_PERCENT)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(ICON_OPACITY_PERCENT, newValue as Int)
            // XaulinXs Customizations: reaplica a opacidade em todos os ícones já na tela
            LauncherAppState.getInstance(context).model.forceReload("xaulinxs_icon_opacity_toggle")
            true
        }
    }
}
'''
    ICON_OPACITY_PREF_KT.write_text(content, encoding="utf-8")
    print(f"[OK] Criado {ICON_OPACITY_PREF_KT.relative_to(REPO_ROOT)}")


def step_create_scrim_opacity_preference_kt():
    require_parent(SCRIM_OPACITY_PREF_KT)
    if SCRIM_OPACITY_PREF_KT.exists() and "ScrimOpacityPreference" in SCRIM_OPACITY_PREF_KT.read_text(encoding="utf-8"):
        print(f"[SKIP] {SCRIM_OPACITY_PREF_KT.relative_to(REPO_ROOT)} já existe.")
        return
    content = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.theme.SCRIM_OPACITY_MAX_PERCENT
import com.xaulinxs.customizations.theme.SCRIM_OPACITY_MIN_PERCENT
import com.xaulinxs.customizations.theme.SCRIM_OPACITY_PERCENT

class ScrimOpacityPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = SCRIM_OPACITY_MIN_PERCENT
        max = SCRIM_OPACITY_MAX_PERCENT
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(SCRIM_OPACITY_PERCENT)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(SCRIM_OPACITY_PERCENT, newValue as Int)
            // XaulinXs Customizations: não precisa forçar nada — a cor do véu é
            // recalculada do zero toda vez que o App Drawer abre
            // (AllAppsState.getWorkspaceScrimColor() -> WallpaperScrimHelper.getScrimColor()).
            true
        }
    }
}
'''
    SCRIM_OPACITY_PREF_KT.write_text(content, encoding="utf-8")
    print(f"[OK] Criado {SCRIM_OPACITY_PREF_KT.relative_to(REPO_ROOT)}")


def step_patch_scrim_helper():
    require_file(SCRIM_HELPER_KT)
    text = SCRIM_HELPER_KT.read_text(encoding="utf-8")
    if "SCRIM_OPACITY_PERCENT" in text:
        print(f"[SKIP] {SCRIM_HELPER_KT.relative_to(REPO_ROOT)} já tem SCRIM_OPACITY_PERCENT.")
        return

    old_imports = (
        "import android.content.Context\n"
        "import androidx.core.graphics.ColorUtils\n"
        "import com.android.launcher3.LauncherPrefs\n"
        "import com.android.launcher3.Utilities\n"
        "import com.android.launcher3.util.WallpaperColorHints\n"
        "import com.xaulinxs.customizations.settings.ThemedScrimPreference.Companion.THEMED_SCRIM_ENABLED\n"
    )
    new_imports = old_imports + (
        "import com.android.launcher3.LauncherPrefs.Companion.backedUpItem\n"
    )
    apply_replace(SCRIM_HELPER_KT, old_imports, new_imports, "WallpaperScrimHelper: import de backedUpItem")

    old_consts = (
        "private const val SCRIM_ALPHA_LIGHT = 140\n"
        "private const val SCRIM_ALPHA_DARK = 160\n"
        "private const val SHADE_RATIO_LIGHT = 0.15f\n"
        "private const val SHADE_RATIO_DARK = 0.55f\n"
    )
    new_consts = old_consts + (
        "\n"
        "// XaulinXs Customizations: percentual de opacidade do véu escolhido pelo\n"
        "// usuário no slider \"Transparência do fundo do menu de apps\". 100%\n"
        "// preserva o alpha original (SCRIM_ALPHA_LIGHT/DARK acima); 0% deixa o véu\n"
        "// totalmente transparente (só o blur real do XaulinXsDepthController fica visível).\n"
        "const val SCRIM_OPACITY_MIN_PERCENT = 0\n"
        "const val SCRIM_OPACITY_MAX_PERCENT = 100\n"
        "private const val KEY_SCRIM_OPACITY_PERCENT = \"xaulinxs_scrim_opacity_percent\"\n"
        "val SCRIM_OPACITY_PERCENT = backedUpItem(KEY_SCRIM_OPACITY_PERCENT, SCRIM_OPACITY_MAX_PERCENT)\n"
    )
    apply_replace(SCRIM_HELPER_KT, old_consts, new_consts, "WallpaperScrimHelper: constante de opacidade")

    old_alpha = (
        "        val alpha = if (isDark) SCRIM_ALPHA_DARK else SCRIM_ALPHA_LIGHT\n"
        "        return ColorUtils.setAlphaComponent(shaded, alpha)\n"
    )
    new_alpha = (
        "        val baseAlpha = if (isDark) SCRIM_ALPHA_DARK else SCRIM_ALPHA_LIGHT\n"
        "        // XaulinXs Customizations: escala o alpha base pelo percentual do slider.\n"
        "        val opacityPercent = LauncherPrefs.get(context).get(SCRIM_OPACITY_PERCENT)\n"
        "            .coerceIn(SCRIM_OPACITY_MIN_PERCENT, SCRIM_OPACITY_MAX_PERCENT)\n"
        "        val alpha = (baseAlpha * opacityPercent / 100).coerceIn(0, 255)\n"
        "        return ColorUtils.setAlphaComponent(shaded, alpha)\n"
    )
    apply_replace(SCRIM_HELPER_KT, old_alpha, new_alpha, "WallpaperScrimHelper: aplicar multiplicador de opacidade")


def step_patch_bubble_text_view():
    require_file(BUBBLE_TEXT_VIEW)
    text = BUBBLE_TEXT_VIEW.read_text(encoding="utf-8")
    if "XaulinXsIconOpacity" in text:
        print(f"[SKIP] {BUBBLE_TEXT_VIEW.relative_to(REPO_ROOT)} já tem o hook do XaulinXsIconOpacity.")
        return
    old = (
        "        icon.setBounds(0, 0, mIconSize, mIconSize);\n"
        "\n"
        "        updateIcon(icon);\n"
    )
    new = (
        "        icon.setBounds(0, 0, mIconSize, mIconSize);\n"
        "        // XaulinXs Customizations: aplica a opacidade de ícone escolhida pelo usuário\n"
        "        icon.setAlpha(com.xaulinxs.customizations.icons.XaulinXsIconOpacity.getAlpha(getContext()));\n"
        "\n"
        "        updateIcon(icon);\n"
    )
    apply_replace(BUBBLE_TEXT_VIEW, old, new, "BubbleTextView.java: hook em applyCompoundDrawables()")


def step_patch_prefs_xml():
    require_file(PREFS_XML)
    text = PREFS_XML.read_text(encoding="utf-8")
    if "IconOpacityPreference" in text and "ScrimOpacityPreference" in text:
        print(f"[SKIP] {PREFS_XML.relative_to(REPO_ROOT)} já tem os sliders de transparência.")
        return
    old = (
        "    </PreferenceScreen>\n"
        "    <!-- ============ XaulinXs Customizations — fim ============ -->\n"
    )
    new = (
        "        <com.xaulinxs.customizations.settings.IconOpacityPreference\n"
        "            android:key=\"xaulinxs_icon_opacity\"\n"
        "            android:title=\"@string/xaulinxs_icon_opacity_title\"\n"
        "            android:summary=\"@string/xaulinxs_icon_opacity_summary\"\n"
        "            android:persistent=\"false\" />\n"
        "\n"
        "        <com.xaulinxs.customizations.settings.ScrimOpacityPreference\n"
        "            android:key=\"xaulinxs_scrim_opacity\"\n"
        "            android:title=\"@string/xaulinxs_scrim_opacity_title\"\n"
        "            android:summary=\"@string/xaulinxs_scrim_opacity_summary\"\n"
        "            android:persistent=\"false\" />\n"
        "\n"
    ) + old
    apply_replace(PREFS_XML, old, new, "launcher_preferences.xml: sliders de transparência")


def step_patch_strings_xml():
    require_file(STRINGS_XML)
    text = STRINGS_XML.read_text(encoding="utf-8")
    if "xaulinxs_icon_opacity_title" in text:
        print(f"[SKIP] {STRINGS_XML.relative_to(REPO_ROOT)} já tem as strings dos sliders.")
        return
    content = text.rstrip("\n")
    if not content.endswith("</resources>"):
        fail(f"{STRINGS_XML} não termina com </resources> como esperado — cole o conteúdo atual pra eu ajustar.")
    body = content[: -len("</resources>")]
    new_content = (
        body
        + '    <string name="xaulinxs_icon_opacity_title">Transparência dos ícones</string>\n'
        + '    <string name="xaulinxs_icon_opacity_summary">Ajusta a opacidade dos ícones de 0% a 100%</string>\n'
        + '    <string name="xaulinxs_scrim_opacity_title">Transparência do fundo do menu de apps</string>\n'
        + '    <string name="xaulinxs_scrim_opacity_summary">Ajusta a opacidade do véu atrás da gaveta de apps (aplica na próxima vez que abrir)</string>\n'
        + "</resources>\n"
    )
    STRINGS_XML.write_text(new_content, encoding="utf-8")
    print(f"[OK] {STRINGS_XML.relative_to(REPO_ROOT)}: strings dos sliders adicionadas")


def main():
    print("== Feature: transparência de ícones e do fundo do menu de apps ==")
    step_create_icon_opacity_kt()
    step_create_icon_opacity_preference_kt()
    step_create_scrim_opacity_preference_kt()
    step_patch_scrim_helper()
    step_patch_bubble_text_view()
    step_patch_prefs_xml()
    step_patch_strings_xml()
    print("\nConcluído. Recompile com:")
    print("  ./gradlew assembleNoQuickstepDebug --stacktrace 2>&1 | tee build_nextNN.log")


if __name__ == "__main__":
    main()
