#!/usr/bin/env python3
"""
Feature: Aumentar/diminuir tamanho dos ícones (até 200%).

Não reinventa o grid do launcher: reaproveita o mesmo mecanismo que já existe
no AOSP para overrides de tamanho de ícone via partner customization
(InvariantDeviceProfile.applyPartnerDeviceProfileOverrides / this.iconSize[]),
e o mesmo pipeline de "recalcular tudo e notificar" que a troca de grid usa
(InvariantDeviceProfile.onConfigChanged(), hoje privado).

Diferença importante em relação ao override de partner: além de escalar
iconSize[], este patch RECALCULA iconBitmapSize/fillResIconDpi na sequência.
O código original de partner override NÃO faz isso (o bitmap continua sendo
gerado no tamanho antigo) — o que é inofensivo pra overrides pequenos de
partner, mas pixelizaria muito em 200%. Ver comentário no método novo.

O que este script faz:
1. Cria modules/customizations/.../icons/XaulinXsIconScale.kt (novo) — guarda
   e valida o percentual (100-200) via LauncherPrefs.
2. Cria modules/customizations/.../settings/IconScalePreference.kt (novo) —
   SeekBarPreference (100-200) que persiste o valor e força o recalculo do
   InvariantDeviceProfile.
3. Edita InvariantDeviceProfile.java (AOSP) — 1 linha de chamada + 1 método
   novo (aplica o multiplicador e recalcula iconBitmapSize/fillResIconDpi) e
   1 método público novo (onXaulinXsIconScaleChanged, wrapper de
   onConfigChanged() que já existe e já é privado).
4. Edita res/xml/launcher_preferences.xml — adiciona o slider na tela
   "XaulinXs Customizations" já existente.
5. Edita res/values/xaulinxs_strings.xml — adiciona título/resumo do slider.

Idempotente. Rode a partir da RAIZ do repositório:
    python3 feature_icon_scale.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

ICON_SCALE_KT = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/icons/XaulinXsIconScale.kt"
ICON_SCALE_PREF_KT = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/settings/IconScalePreference.kt"
IDP_JAVA = REPO_ROOT / "src/com/android/launcher3/InvariantDeviceProfile.java"
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


def step_create_icon_scale_kt():
    require_parent(ICON_SCALE_KT)
    if ICON_SCALE_KT.exists() and "getScalePercent" in ICON_SCALE_KT.read_text(encoding="utf-8"):
        print(f"[SKIP] {ICON_SCALE_KT.relative_to(REPO_ROOT)} já existe.")
        return
    content = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Guarda e valida o percentual de escala de ícone (100%-200%) escolhido pelo
 * usuário. Lido por InvariantDeviceProfile.applyXaulinXsIconScaleOverride()
 * (edição cirúrgica em InvariantDeviceProfile.java) e escrito pela
 * com.xaulinxs.customizations.settings.IconScalePreference.
 */
package com.xaulinxs.customizations.icons

import android.content.Context
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

object XaulinXsIconScale {
    private const val KEY_ICON_SCALE_PERCENT = "xaulinxs_icon_scale_percent"
    const val MIN_PERCENT = 100
    const val MAX_PERCENT = 200

    @JvmField
    val ICON_SCALE_PERCENT = backedUpItem(KEY_ICON_SCALE_PERCENT, MIN_PERCENT)

    @JvmStatic
    fun getScalePercent(context: Context): Int {
        val stored = LauncherPrefs.get(context).get(ICON_SCALE_PERCENT)
        return stored.coerceIn(MIN_PERCENT, MAX_PERCENT)
    }
}
'''
    ICON_SCALE_KT.write_text(content, encoding="utf-8")
    print(f"[OK] Criado {ICON_SCALE_KT.relative_to(REPO_ROOT)}")


def step_create_icon_scale_preference_kt():
    require_parent(ICON_SCALE_PREF_KT)
    if ICON_SCALE_PREF_KT.exists() and "IconScalePreference" in ICON_SCALE_PREF_KT.read_text(encoding="utf-8"):
        print(f"[SKIP] {ICON_SCALE_PREF_KT.relative_to(REPO_ROOT)} já existe.")
        return
    content = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.InvariantDeviceProfile
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.icons.XaulinXsIconScale
import com.xaulinxs.customizations.icons.XaulinXsIconScale.ICON_SCALE_PERCENT

class IconScalePreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = XaulinXsIconScale.MIN_PERCENT
        max = XaulinXsIconScale.MAX_PERCENT
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(ICON_SCALE_PERCENT)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(ICON_SCALE_PERCENT, newValue as Int)
            // XaulinXs Customizations: recalcula o grid/ícone com o novo tamanho
            InvariantDeviceProfile.INSTANCE.get(context).onXaulinXsIconScaleChanged()
            true
        }
    }
}
'''
    ICON_SCALE_PREF_KT.write_text(content, encoding="utf-8")
    print(f"[OK] Criado {ICON_SCALE_PREF_KT.relative_to(REPO_ROOT)}")


def step_patch_idp():
    require_file(IDP_JAVA)
    text = IDP_JAVA.read_text(encoding="utf-8")
    if "applyXaulinXsIconScaleOverride" in text:
        print(f"[SKIP] {IDP_JAVA.relative_to(REPO_ROOT)} já tem applyXaulinXsIconScaleOverride.")
        return

    # 1) Chamada logo após o override de partner, no mesmo ponto do pipeline.
    old_call = (
        "        // If the partner customization apk contains any grid overrides, apply them\n"
        "        // Supported overrides: numRows, numColumns, iconSize\n"
        "        applyPartnerDeviceProfileOverrides(context, metrics);\n"
    )
    new_call = old_call + (
        "        // XaulinXs Customizations: aplica o multiplicador de tamanho de ícone\n"
        "        // (100%-200%) escolhido pelo usuário. Tem que vir depois do override de\n"
        "        // partner acima (mesma convenção) e recalcula iconBitmapSize/fillResIconDpi\n"
        "        // na sequência — diferente do override de partner, que não recalcula e\n"
        "        // pixelizaria em valores altos.\n"
        "        applyXaulinXsIconScaleOverride(context, metrics);\n"
    )
    apply_replace(IDP_JAVA, old_call, new_call, "InvariantDeviceProfile: chamada do override de escala")

    # 2) Novo método privado, logo após applyPartnerDeviceProfileOverrides().
    old_method_end = (
        "            if (iconSizePx > 0) {\n"
        "                this.iconSize[INDEX_DEFAULT] = Utilities.dpiFromPx(iconSizePx, dm.densityDpi);\n"
        "            }\n"
        "        } catch (Resources.NotFoundException ex) {\n"
        "            Log.e(TAG, \"Invalid Partner grid resource!\", ex);\n"
        "        }\n"
        "    }\n"
    )
    new_method_end = old_method_end + (
        "\n"
        "    /**\n"
        "     * XaulinXs Customizations — aplica o multiplicador de tamanho de ícone\n"
        "     * (100%-200%) definido pelo usuário em\n"
        "     * com.xaulinxs.customizations.settings.IconScalePreference. Escala todos\n"
        "     * os tamanhos de ícone por tipo de tela (retrato/paisagem/etc.) e\n"
        "     * recalcula iconBitmapSize/fillResIconDpi para o ícone renderizar sem\n"
        "     * pixelizar mesmo em 200%.\n"
        "     */\n"
        "    private void applyXaulinXsIconScaleOverride(Context context, DisplayMetrics dm) {\n"
        "        int percent = com.xaulinxs.customizations.icons.XaulinXsIconScale.getScalePercent(context);\n"
        "        if (percent == 100) {\n"
        "            return;\n"
        "        }\n"
        "        float scale = percent / 100f;\n"
        "        for (int i = 0; i < iconSize.length; i++) {\n"
        "            iconSize[i] = iconSize[i] * scale;\n"
        "        }\n"
        "        float maxIconSize = iconSize[0];\n"
        "        for (int i = 1; i < iconSize.length; i++) {\n"
        "            maxIconSize = Math.max(maxIconSize, iconSize[i]);\n"
        "        }\n"
        "        iconBitmapSize = ResourceUtils.pxFromDp(maxIconSize, dm);\n"
        "        fillResIconDpi = getLauncherIconDensity(iconBitmapSize);\n"
        "    }\n"
    )
    apply_replace(IDP_JAVA, old_method_end, new_method_end, "InvariantDeviceProfile: método applyXaulinXsIconScaleOverride")

    # 3) Wrapper público para disparar o recálculo a partir da preference.
    old_set_grid = (
        "    public void setCurrentGrid(String newGridName) {\n"
        "        if (TextUtils.equals(mPrefs.get(GRID_NAME), newGridName)) return;\n"
        "        mPrefs.put(GRID_NAME, newGridName);\n"
        "        mMainExecutor.execute(() -> {\n"
        "            Trace.beginSection(\"InvariantDeviceProfile#setCurrentGrid\");\n"
        "            onConfigChanged();\n"
        "            Trace.endSection();\n"
        "        });\n"
        "    }\n"
    )
    new_set_grid = old_set_grid + (
        "\n"
        "    /**\n"
        "     * XaulinXs Customizations — força o InvariantDeviceProfile a recalcular\n"
        "     * grid/ícone/bitmap depois que o usuário muda o slider de tamanho de\n"
        "     * ícone. Reaproveita o mesmo pipeline de onConfigChanged() usado pela\n"
        "     * troca de grid (recalcula tudo e notifica os listeners).\n"
        "     */\n"
        "    public void onXaulinXsIconScaleChanged() {\n"
        "        mMainExecutor.execute(() -> onConfigChanged());\n"
        "    }\n"
    )
    apply_replace(IDP_JAVA, old_set_grid, new_set_grid, "InvariantDeviceProfile: wrapper onXaulinXsIconScaleChanged")


def step_patch_prefs_xml():
    require_file(PREFS_XML)
    text = PREFS_XML.read_text(encoding="utf-8")
    if "IconScalePreference" in text:
        print(f"[SKIP] {PREFS_XML.relative_to(REPO_ROOT)} já tem IconScalePreference.")
        return
    old = (
        "        <com.xaulinxs.customizations.settings.ThemedScrimPreference\n"
        "            android:key=\"xaulinxs_themed_scrim\"\n"
        "            android:title=\"@string/xaulinxs_themed_scrim_title\"\n"
        "            android:summary=\"@string/xaulinxs_themed_scrim_summary\"\n"
        "            android:persistent=\"false\" />\n"
    )
    new = old + (
        "\n"
        "        <com.xaulinxs.customizations.settings.IconScalePreference\n"
        "            android:key=\"xaulinxs_icon_scale\"\n"
        "            android:title=\"@string/xaulinxs_icon_scale_title\"\n"
        "            android:summary=\"@string/xaulinxs_icon_scale_summary\"\n"
        "            android:persistent=\"false\" />\n"
    )
    apply_replace(PREFS_XML, old, new, "launcher_preferences.xml: slider de tamanho de ícone")


def step_patch_strings_xml():
    require_file(STRINGS_XML)
    text = STRINGS_XML.read_text(encoding="utf-8")
    if "xaulinxs_icon_scale_title" in text:
        print(f"[SKIP] {STRINGS_XML.relative_to(REPO_ROOT)} já tem as strings do slider.")
        return
    old = '    <string name="xaulinxs_themed_scrim_summary">Aplica um efeito de vidro fosco temático ao papel de parede na tela de apps</string>\n'
    new = old + (
        '    <string name="xaulinxs_icon_scale_title">Tamanho dos ícones</string>\n'
        '    <string name="xaulinxs_icon_scale_summary">Aumenta o tamanho dos ícones até 200% '
        '(valores altos podem sobrepor ícones vizinhos)</string>\n'
    )
    apply_replace(STRINGS_XML, old, new, "xaulinxs_strings.xml: strings do slider")


def main():
    print("== Feature: tamanho dos ícones (100%-200%) ==")
    step_create_icon_scale_kt()
    step_create_icon_scale_preference_kt()
    step_patch_idp()
    step_patch_prefs_xml()
    step_patch_strings_xml()
    print("\nConcluído. Recompile com:")
    print("  ./gradlew assembleNoQuickstepDebug --stacktrace 2>&1 | tee build_nextNN.log")


if __name__ == "__main__":
    main()
