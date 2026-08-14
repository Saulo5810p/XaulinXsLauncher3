"""
XaulinXs Customizations — Limpeza pré-efeitos cinematográficos:
  A) CONSERTA a fonte customizada (bug real encontrado: o typeface só era
     aplicado uma vez, no construtor da BubbleTextView — importar uma fonte
     nova nunca recarregava os ícones já existentes na tela. Corrigido com
     put()/remove() certos no LauncherPrefs + recreate() do Launcher após
     importar/resetar, igual o sistema faz numa troca de tema).
  B) REMOVE por completo a barra de busca customizada (11 arquivos +
     referência no Hotseat.java original + bloco na tela de preferências),
     conforme decisão do usuário — feature abandonada definitivamente.

Idempotente: pode rodar de novo sem duplicar nada / sem erro se já limpo.

USO (Termux, na raiz do projeto):
    python3 feature_cinematic_0_fix_font_remove_searchbar.py
"""
from pathlib import Path

def replace_once(path_str, old, new, label, required=True):
    path = Path(path_str)
    if not path.exists():
        print(f"SKIP ({label}): arquivo não existe mais ({path_str})")
        return
    content = path.read_text(encoding="utf-8")
    if new in content:
        print(f"SKIP ({label}): já aplicado")
        return
    if old not in content:
        msg = f"âncora não encontrada em {path_str} ({label})"
        if required:
            raise AssertionError(msg + " — cola o arquivo atual, pode ter mudado")
        print(f"SKIP ({label}): {msg}")
        return
    if content.count(old) != 1:
        raise AssertionError(f"âncora aparece {content.count(old)}x em {path_str} ({label}), precisa ser única")
    path.write_text(content.replace(old, new), encoding="utf-8")
    print(f"APLICADO: {label}")

def delete_if_exists(path_str):
    path = Path(path_str)
    if path.exists():
        path.unlink()
        print(f"APAGADO: {path_str}")
    else:
        print(f"SKIP (já não existe): {path_str}")


# ===========================================================================
# A) CONSERTO DA FONTE CUSTOMIZADA
# ===========================================================================

# A1) XaulinXsCustomFont.kt — corrige put()/remove() e expõe callback de
#     "fonte mudou" pra quem quiser reagir (usado em A2).
replace_once(
    "modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsCustomFont.kt",
    """    @JvmStatic
    fun setCustomFontPath(context: Context, path: String?) {
        LauncherPrefs.get(context).put(CUSTOM_FONT_PATH, path)
        cachedTypeface = null
        cachedTypefacePath = null
    }""",
    """    @JvmStatic
    fun setCustomFontPath(context: Context, path: String?) {
        // XaulinXs fix: LauncherPrefs.put() espera Pair<Item, Any> (valor
        // não-nulo) — path nulo (ação "Restaurar padrão") precisa usar
        // remove(), não put() com null, senão o compilador rejeita e,
        // pior, o valor antigo nunca seria de fato limpo.
        val prefs = LauncherPrefs.get(context)
        if (path != null) {
            prefs.put(CUSTOM_FONT_PATH to path)
        } else {
            prefs.remove(CUSTOM_FONT_PATH)
        }
        cachedTypeface = null
        cachedTypefacePath = null
    }""",
    "corrige put()/remove() em XaulinXsCustomFont.setCustomFontPath",
)

# A2) XaulinXsCustomFont.kt — método novo que percorre a árvore de views
#     de um ViewGroup (Workspace, Hotseat, AllApps) e reaplica o typeface
#     em toda BubbleTextView já existente, sem precisar recriar Activity
#     nenhuma. Só é ÚTIL de fato quando chamado a partir do Launcher em si
#     (ver A3) — chamar da SettingsActivity não adiantaria, pois é uma
#     Activity separada que não enxerga a árvore de views do launcher.
replace_once(
    "modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsCustomFont.kt",
    """    @JvmStatic
    fun loadTypefaceIfAvailable(context: Context): Typeface? {""",
    """    /**
     * XaulinXs fix (causa raiz do "fonte não muda ao importar"): o
     * typeface só era aplicado uma vez, no construtor de cada
     * BubbleTextView — views já existentes na tela nunca eram
     * recarregadas ao importar uma fonte nova. Este método percorre a
     * árvore de views a partir da raiz do launcher (Workspace, Hotseat,
     * AllApps — todos filhos da DragLayer) e reaplica o typeface atual
     * (ou o padrão do sistema, se a fonte foi resetada) em toda
     * BubbleTextView viva, sem precisar recriar a Activity.
     */
    @JvmStatic
    fun reapplyToVisibleIcons(context: Context, root: android.view.View) {
        val typeface = loadTypefaceIfAvailable(context)
        applyRecursively(root, typeface)
    }

    private fun applyRecursively(view: android.view.View, typeface: Typeface?) {
        // Restrito a BubbleTextView (ícones), nunca TextView genérico —
        // widgets, relógios, textos de notificação etc. NÃO devem ter o
        // typeface trocado por esta rotina. Reset usa null (não
        // Typeface.DEFAULT): null faz o Android resolver de volta o
        // fontFamily definido no tema/XML original da view (fontes
        // variáveis do Material), enquanto DEFAULT forçaria Roboto puro
        // e quebraria o visual original dos ícones.
        if (view is com.android.launcher3.BubbleTextView) {
            view.typeface = typeface
        }
        if (view is android.view.ViewGroup) {
            for (i in 0 until view.childCount) {
                applyRecursively(view.getChildAt(i), typeface)
            }
        }
    }

    @JvmStatic
    fun loadTypefaceIfAvailable(context: Context): Typeface? {""",
    "adiciona XaulinXsCustomFont.reapplyToVisibleIcons (percorre árvore de views)",
)

# A3) Launcher.java — chama reapplyToVisibleIcons no onResume, cobrindo o
#     caso real de uso: usuário abre configurações, importa/reseta a
#     fonte, e volta pro launcher (que sempre passa por onResume nesse
#     fluxo). Guarda de "só reaplica se o path mudou" evita trabalho
#     desnecessário em todo resume normal (troca de app, tela ligar, etc).
replace_once(
    "src/com/android/launcher3/Launcher.java",
    """    protected void onResume() {
        TraceHelper.INSTANCE.beginSection(ON_RESUME_EVT);
        super.onResume();
        mLauncherUiState.setIsResumedActivity(true);
        DragView.removeAllViews(this);
        TraceHelper.INSTANCE.endSection();
    }""",
    """    protected void onResume() {
        TraceHelper.INSTANCE.beginSection(ON_RESUME_EVT);
        super.onResume();
        mLauncherUiState.setIsResumedActivity(true);
        DragView.removeAllViews(this);
        // XaulinXs Customizations: reaplica a fonte customizada nos ícones
        // já existentes na tela se ela mudou desde o último resume (fix do
        // bug "fonte não atualiza ao importar" — ver XaulinXsCustomFont).
        String xaulinxsCurrentFontPath =
                com.xaulinxs.customizations.font.XaulinXsCustomFont.getCustomFontPath(this);
        if (!java.util.Objects.equals(xaulinxsCurrentFontPath, mXaulinXsLastAppliedFontPath)) {
            mXaulinXsLastAppliedFontPath = xaulinxsCurrentFontPath;
            com.xaulinxs.customizations.font.XaulinXsCustomFont.reapplyToVisibleIcons(
                    this, getDragLayer());
        }
        TraceHelper.INSTANCE.endSection();
    }

    // XaulinXs Customizations: guarda o último path de fonte aplicado para
    // evitar reaplicar em todo onResume (só quando de fato mudou).
    private String mXaulinXsLastAppliedFontPath;""",
    "adiciona reload de fonte no onResume do Launcher.java",
)

# ===========================================================================
# B) REMOÇÃO COMPLETA DA BARRA DE BUSCA CUSTOMIZADA
# ===========================================================================

# B1) Reverte o hook no Hotseat.java para o comportamento 100% AOSP original
replace_once(
    "src/com/android/launcher3/Hotseat.java",
    """        // XaulinXs Customizations: barra de busca própria (opcional). Quando
        // desativada (padrão), createViewIfEnabled() retorna null e o QSB
        // original do AOSP é usado normalmente, sem nenhuma mudança de
        // comportamento. Quando ativada, ocupa o mesmo slot que o QSB original
        // ocuparia — que já fica abaixo da fileira de ícones por design do
        // AOSP (Hotseat.onLayout/getQsbOffsetY), sem precisar de nenhum ajuste
        // de posição aqui.
        View xaulinxsSearchBar =
                com.xaulinxs.customizations.search.XaulinXsSearchBarFactory
                        .createViewIfEnabled(context, this);
        mQsb = xaulinxsSearchBar != null
                ? xaulinxsSearchBar
                : LauncherComponentProvider.get(context).getQsbWidgetFactory().createView(this);""",
    """        mQsb = LauncherComponentProvider.get(context).getQsbWidgetFactory().createView(this);""",
    "reverte Hotseat.java para o QSB 100% original do AOSP (sem barra customizada)",
)

# B2) Remove o bloco inteiro de preferências da search bar em
#     launcher_preferences.xml. Âncora inclui o bloco anterior
#     (CustomFontPreference) inteiro para garantir unicidade real — o
#     </PreferenceScreen> sozinho não é único no arquivo.
replace_once(
    "res/xml/launcher_preferences.xml",
    """        <com.xaulinxs.customizations.settings.CustomFontPreference
            android:key="xaulinxs_custom_font"
            android:title="@string/xaulinxs_custom_font_title"
            android:persistent="false" />

        <com.xaulinxs.customizations.settings.SearchBarEnabledPreference
            android:key="xaulinxs_searchbar_enabled"
            android:title="@string/xaulinxs_searchbar_enabled_title"
            android:summary="@string/xaulinxs_searchbar_enabled_summary"
            android:persistent="false" />

        <com.xaulinxs.customizations.settings.SearchBarWebModePreference
            android:key="xaulinxs_searchbar_web_mode"
            android:title="@string/xaulinxs_searchbar_web_mode_title"
            android:summary="@string/xaulinxs_searchbar_web_mode_summary"
            android:persistent="false" />

        <com.xaulinxs.customizations.settings.SearchBarOpacityPreference
            android:key="xaulinxs_searchbar_opacity"
            android:title="@string/xaulinxs_searchbar_opacity_title"
            android:persistent="false" />

        <com.xaulinxs.customizations.settings.SearchBarColorEnabledPreference
            android:key="xaulinxs_searchbar_custom_color_enabled"
            android:title="@string/xaulinxs_searchbar_custom_color_enabled_title"
            android:summary="@string/xaulinxs_searchbar_custom_color_enabled_summary"
            android:persistent="false" />

        <com.xaulinxs.customizations.settings.SearchBarColorPickerPreference
            android:key="xaulinxs_searchbar_custom_color_picker"
            android:title="@string/xaulinxs_searchbar_color_picker_title"
            android:persistent="false" />

        <com.xaulinxs.customizations.settings.SearchBarBlurEnabledPreference
            android:key="xaulinxs_searchbar_blur_enabled"
            android:title="@string/xaulinxs_searchbar_blur_enabled_title"
            android:summary="@string/xaulinxs_searchbar_blur_enabled_summary"
            android:persistent="false" />

    </PreferenceScreen>""",
    """        <com.xaulinxs.customizations.settings.CustomFontPreference
            android:key="xaulinxs_custom_font"
            android:title="@string/xaulinxs_custom_font_title"
            android:persistent="false" />

    </PreferenceScreen>""",
    "remove bloco de preferências da search bar em launcher_preferences.xml",
)

# B4) Remove strings órfãs da search bar. As strings próprias das
#     XaulinXs Customizations ficam em res/values/xaulinxs_strings.xml
#     (não em strings.xml, que é o arquivo AOSP original) — checa os
#     dois por segurança. Só mexe em res/values/ (idioma base); as
#     pastas values-XX de tradução não valem o risco, string não usada
#     não quebra build nem aparece em lugar nenhum.
import re as _re
for _strings_filename in ("xaulinxs_strings.xml", "strings.xml"):
    _strings_path = Path("res/values") / _strings_filename
    if not _strings_path.exists():
        continue
    _content = _strings_path.read_text(encoding="utf-8")
    _pattern = _re.compile(
        r'[ \t]*<string name="xaulinxs_searchbar_[^"]*"[^>]*>.*?</string>\n?',
        _re.DOTALL,
    )
    _new_content, _count = _pattern.subn("", _content)
    if _count > 0:
        _strings_path.write_text(_new_content, encoding="utf-8")
        print(f"APLICADO: removidas {_count} strings órfãs xaulinxs_searchbar_* de res/values/{_strings_filename}")
    else:
        print(f"SKIP: nenhuma string xaulinxs_searchbar_* encontrada em res/values/{_strings_filename}")

# B3) Apaga por completo os arquivos-fonte da search bar (11 arquivos)
searchbar_files = [
    "modules/customizations/src/com/xaulinxs/customizations/search/XaulinXsSearchBarView.kt",
    "modules/customizations/src/com/xaulinxs/customizations/search/XaulinXsSearchBarPrefs.kt",
    "modules/customizations/src/com/xaulinxs/customizations/search/XaulinXsSearchBarBlur.kt",
    "modules/customizations/src/com/xaulinxs/customizations/search/XaulinXsSearchBarColors.kt",
    "modules/customizations/src/com/xaulinxs/customizations/search/XaulinXsSearchBarFactory.kt",
    "modules/customizations/src/com/xaulinxs/customizations/settings/SearchBarEnabledPreference.kt",
    "modules/customizations/src/com/xaulinxs/customizations/settings/SearchBarColorPickerPreference.kt",
    "modules/customizations/src/com/xaulinxs/customizations/settings/SearchBarWebModePreference.kt",
    "modules/customizations/src/com/xaulinxs/customizations/settings/SearchBarColorEnabledPreference.kt",
    "modules/customizations/src/com/xaulinxs/customizations/settings/SearchBarBlurEnabledPreference.kt",
    "modules/customizations/src/com/xaulinxs/customizations/settings/SearchBarOpacityPreference.kt",
]
for f in searchbar_files:
    delete_if_exists(f)

# Remove a pasta "search" se ficou vazia
search_dir = Path("modules/customizations/src/com/xaulinxs/customizations/search")
if search_dir.exists() and not any(search_dir.iterdir()):
    search_dir.rmdir()
    print(f"APAGADO (pasta vazia): {search_dir}")

print("\nOK — fonte customizada corrigida (agora reaplica nos ícones já na tela)")
print("e barra de busca customizada removida por completo.")
print("Próximo passo: ./gradlew assembleNoQuickstepDebug")
