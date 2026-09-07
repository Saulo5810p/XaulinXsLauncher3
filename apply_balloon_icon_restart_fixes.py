#!/usr/bin/env python3
"""
apply_balloon_icon_restart_fixes.py

Aplica 3 correções/features sobre o repo XaulinXsLauncher3, rodando na
raiz do projeto (onde fica a pasta res/, src/, modules/):

1) BALÕES BRANCOS (workspace + gaveta/opções) — o fix anterior só cobria
   o ramo "else" (gaveta de apps/pastas) de ArrowPopup.java. A workspace
   usa o ramo canUseMultipleShadesForPopup()==true, que ainda lia cor
   estática — por isso continuava branco lá. Também faltava mArrowColor
   (a seta do balão), que nunca tinha sido coberto. Agora os 3 pontos
   (seta, corpo em modo "shades", corpo em modo single) seguem a mesma
   prioridade: cor manual > extraída do wallpaper > fallback AOSP.

2) FUNDO DOS ÍCONES NÃO REMOVIDO — o fix anterior só cobria ícones
   LEGADOS embrulhados sinteticamente (wrapToAdaptiveIcon). Ícones que já
   chegam como AdaptiveIconDrawable de verdade, mas com um background
   próprio de cor opaca (não transparente), não eram tocados. Agora,
   depois de resolver tempIcon (embrulhado ou não), qualquer
   AdaptiveIconDrawable com background ColorDrawable opaco tem o fundo
   trocado por transparente quando a opção está ligada — cobre "todo e
   qualquer ícone que tiver um fundo".

3) BOTÃO "REINICIAR PARA APLICAR ALTERAÇÕES" — novo item de menu no
   canto superior da Toolbar, visível só na tela raiz de configurações
   (não em sub-telas). Reinicia o PROCESSO inteiro (não só a Activity),
   necessário para customizações que dependem de estado carregado uma
   vez no Application/cache de ícones.

Idempotente: cada fix checa um marcador antes de aplicar; rodar de novo
não duplica nem quebra nada já corrigido. Se algum arquivo-alvo não bater
com o texto esperado (por já ter sido editado manualmente de outra
forma), o fix correspondente é pulado com aviso — os outros continuam.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def apply_unique_replace(path: Path, old: str, new: str, marker: str, label: str) -> str:
    """Aplica old->new em path, checando idempotência via marker.
    Retorna: 'applied' | 'already' | 'skipped-mismatch' | 'skipped-missing'
    """
    if not path.exists():
        print(f"  [PULADO] {label}: arquivo não encontrado ({path.relative_to(ROOT)})")
        return "skipped-missing"
    text = read(path)
    if marker in text:
        return "already"
    count = text.count(old)
    if count != 1:
        print(f"  [PULADO] {label}: texto esperado não encontrado (ou duplicado) em "
              f"{path.relative_to(ROOT)} — provável edição manual anterior. "
              f"Corrija manualmente ou peça um novo script.")
        return "skipped-mismatch"
    write(path, text.replace(old, new, 1))
    return "applied"


def fix_1_balloon_colors():
    print("=== Fix 1: balões brancos (workspace + gaveta) ===")
    path = ROOT / "src" / "com" / "android" / "launcher3" / "popup" / "ArrowPopup.java"

    # 1a) mArrowColor
    old_a = (
        '        // Initialize arrow view\n'
        '        final Resources resources = getResources();\n'
        '        mArrowColor = getContext().getColor(R.color.materialColorSurfaceContainer);\n'
    )
    new_a = (
        '        // Initialize arrow view\n'
        '        final Resources resources = getResources();\n'
        '        // XaulinXs fix (info.txt: "Balões na workspace e nas opções do\n'
        '        // Launcher3 estão brancos"): mArrowColor tinha ficado de fora do\n'
        '        // primeiro fix — a seta do balão continuava lendo\n'
        '        // materialColorSurfaceContainer direto, então mesmo com o corpo\n'
        '        // do balão já corrigido a ponta ainda aparecia branca/destoante.\n'
        '        // Mesma prioridade das outras cores do balão: override manual >\n'
        '        // extração do wallpaper > fallback AOSP original.\n'
        '        Integer xaulinxsArrowColor =\n'
        '                com.xaulinxs.customizations.theme.XaulinXsBalloonColor\n'
        '                        .getBalloonColorOverride(getContext());\n'
        '        mArrowColor = xaulinxsArrowColor != null\n'
        '                ? xaulinxsArrowColor\n'
        '                : getContext().getColor(R.color.materialColorSurfaceContainer);\n'
    )
    marker_a = "XaulinXs fix (info.txt: \"Balões na workspace"
    r1 = apply_unique_replace(path, old_a, new_a, marker_a, "1a (mArrowColor)")

    # 1b) ramo canUseMultipleShadesForPopup (workspace)
    old_b = (
        '        if (mActivityContext.canUseMultipleShadesForPopup()) {\n'
        '            mColors = new int[]{\n'
        '                    getContext().getColor(R.color.popup_shade_first),\n'
        '                    getContext().getColor(R.color.popup_shade_second),\n'
        '                    getContext().getColor(R.color.popup_shade_third)\n'
        '            };\n'
        '        } else {\n'
    )
    new_b = (
        '        if (mActivityContext.canUseMultipleShadesForPopup()) {\n'
        '            // XaulinXs fix (info.txt: "Balões na workspace e nas opções do\n'
        '            // Launcher3 estão brancos"): este é o ramo REALMENTE usado nos\n'
        '            // balões da workspace (canUseMultipleShadesForPopup() retorna\n'
        '            // true fora da gaveta de apps e fora de pastas — exatamente o\n'
        '            // caso "workspace" relatado) — o fix anterior só cobriu o\n'
        '            // ramo "else" (gaveta de apps/pastas), por isso a workspace\n'
        '            // continuava branca mesmo depois do primeiro fix. Quando há\n'
        '            // override (manual ou extraído do wallpaper), usamos a mesma\n'
        '            // cor sólida nos 3 tons — não faz sentido gerar 3 sombras\n'
        '            // diferentes a partir de um recurso estático quando o usuário\n'
        '            // já escolheu (ou o wallpaper já definiu) uma cor específica;\n'
        '            // cai pro comportamento AOSP original (3 tons estáticos) só\n'
        '            // quando não há nenhuma extração/override disponível.\n'
        '            Integer xaulinxsShadeColor =\n'
        '                    com.xaulinxs.customizations.theme.XaulinXsBalloonColor\n'
        '                            .getBalloonColorOverride(getContext());\n'
        '            mColors = xaulinxsShadeColor != null\n'
        '                    ? new int[]{xaulinxsShadeColor, xaulinxsShadeColor, xaulinxsShadeColor}\n'
        '                    : new int[]{\n'
        '                            getContext().getColor(R.color.popup_shade_first),\n'
        '                            getContext().getColor(R.color.popup_shade_second),\n'
        '                            getContext().getColor(R.color.popup_shade_third)\n'
        '                    };\n'
        '        } else {\n'
    )
    marker_b = "este é o ramo REALMENTE usado nos"
    r2 = apply_unique_replace(path, old_b, new_b, marker_b, "1b (workspace shades)")

    for r in (r1, r2):
        if r == "already":
            print("  já aplicado, pulando.")
    if "applied" in (r1, r2):
        print("  aplicado.")


def fix_2_icon_background():
    print("=== Fix 2: remoção de fundo para todo e qualquer ícone ===")
    path = ROOT / "iconloader" / "src" / "com" / "android" / "launcher3" / "icons" / "BaseIconFactory.kt"
    old = (
        '        if (options.wrapNonAdaptiveIcon) {\n'
        '            // XaulinXs: registra ANTES de embrulhar se este ícone era legado\n'
        '            // (não-adaptativo) — depois do wrap ele sempre vira um\n'
        '            // AdaptiveIconDrawable, então esse é o único ponto em que dá\n'
        '            // pra saber a diferença. Usado logo abaixo em drawableToBitmap\n'
        '            // pra decidir se pula a sombra sintética deste ícone\n'
        '            // específico (feature "remover fundo/sombra dos ícones",\n'
        '            // info.txt/etapa 3).\n'
        '            options.xaulinxsLegacyIconWrapped = tempIcon !is AdaptiveIconDrawable\n'
        '            tempIcon = wrapToAdaptiveIcon(tempIcon, options)\n'
        '        }\n'
        '\n'
        '        val drawFullBleed = options.drawFullBleed ?: drawFullBleedIcons\n'
    )
    new = (
        '        if (options.wrapNonAdaptiveIcon) {\n'
        '            // XaulinXs: registra ANTES de embrulhar se este ícone era legado\n'
        '            // (não-adaptativo) — depois do wrap ele sempre vira um\n'
        '            // AdaptiveIconDrawable, então esse é o único ponto em que dá\n'
        '            // pra saber a diferença. Usado logo abaixo em drawableToBitmap\n'
        '            // pra decidir se pula a sombra sintética deste ícone\n'
        '            // específico (feature "remover fundo/sombra dos ícones",\n'
        '            // info.txt/etapa 3).\n'
        '            options.xaulinxsLegacyIconWrapped = tempIcon !is AdaptiveIconDrawable\n'
        '            tempIcon = wrapToAdaptiveIcon(tempIcon, options)\n'
        '        }\n'
        '\n'
        '        // XaulinXs fix (info.txt: "Fundo dos ícones não foi removido. Em\n'
        '        // vez de restringir a alguns, aplicar a remoção do fundo para\n'
        '        // todo e qualquer ícone que tiver um"):\n'
        '        //\n'
        '        // O fix anterior só cobria ícones LEGADOS (não-adaptativos) que\n'
        '        // precisavam ser embrulhados sinteticamente em wrapToAdaptiveIcon\n'
        '        // — ali a cor era escolhida na hora de criar o ColorDrawable de\n'
        '        // fundo. Mas isso não cobre um caso comum: apps que já entregam\n'
        '        // um AdaptiveIconDrawable de verdade (options.wrapNonAdaptiveIcon\n'
        '        // nunca embrulha nada, `icon as? AdaptiveIconDrawable` já\n'
        '        // retorna o próprio ícone), cuja layer de `background` é uma cor\n'
        '        // sólida opaca própria do app (branco, cinza, etc.) em vez de\n'
        '        // transparente. Esse ícone tecnicamente "tem" um fundo mesmo sem\n'
        '        // passar pelo wrapper sintético.\n'
        '        //\n'
        '        // Fix genérico: depois que tempIcon já está resolvido (embrulhado\n'
        '        // ou não), se a opção estiver ligada e ele for um\n'
        '        // AdaptiveIconDrawable cujo background é um ColorDrawable OPACO\n'
        '        // (alpha 255 — não mexe em fundos já parcialmente/totalmente\n'
        '        // transparentes, que não são o problema relatado), substitui o\n'
        '        // background por transparente. Cobre tanto o caso já embrulhado\n'
        '        // (branco sintético de wrapToAdaptiveIcon) quanto o ícone\n'
        '        // adaptativo real de terceiros com fundo opaco próprio — "todo e\n'
        '        // qualquer ícone que tiver um fundo", como pedido.\n'
        '        if (tempIcon is AdaptiveIconDrawable &&\n'
        '            com.xaulinxs.customizations.icons.XaulinXsLegacyIconAppearance\n'
        '                .shouldRemoveBackgroundAndShadow(context)\n'
        '        ) {\n'
        '            val bg = tempIcon.background\n'
        '            if (bg is ColorDrawable && Color.alpha(bg.color) == 255) {\n'
        '                tempIcon = AdaptiveIconDrawable(ColorDrawable(Color.TRANSPARENT), tempIcon.foreground)\n'
        '                    .apply { bounds = icon.bounds }\n'
        '                // Ícone adaptativo real com fundo próprio removido aqui —\n'
        '                // ainda pode ter sombra sintética desenhada em\n'
        '                // drawableToBitmap (que só pula a sombra quando\n'
        '                // xaulinxsLegacyIconWrapped é true, ou seja, só para o\n'
        '                // caso do wrap sintético). Marca também este caso como\n'
        '                // "legado" para fins de sombra: um ícone que teve seu\n'
        '                // fundo removido não deve manter uma sombra desenhada em\n'
        '                // torno de uma máscara que já não tem fundo visível atrás.\n'
        '                options.xaulinxsLegacyIconWrapped = true\n'
        '            }\n'
        '        }\n'
        '\n'
        '        val drawFullBleed = options.drawFullBleed ?: drawFullBleedIcons\n'
    )
    marker = "options.xaulinxsLegacyIconWrapped = true"
    r = apply_unique_replace(path, old, new, marker, "2 (icon background)")
    if r == "already":
        print("  já aplicado, pulando.")
    elif r == "applied":
        print("  aplicado.")


def fix_3_restart_button():
    print("=== Fix 3: botão 'Reiniciar para aplicar alterações' ===")

    # 3a) string
    strings_path = ROOT / "res" / "values" / "xaulinxs_strings.xml"
    old_s = '    <string name="xaulinxs_customizations_summary">Make your idea your own</string>\n'
    new_s = (
        '    <string name="xaulinxs_customizations_summary">Make your idea your own</string>\n'
        '    <!-- XaulinXs: botão no canto superior da tela principal de\n'
        '         configurações, reinicia o app pra aplicar customizações que\n'
        '         exigem reinício (não só recriação da tela de Configurações). -->\n'
        '    <string name="xaulinxs_restart_app_title">Reiniciar para aplicar alterações</string>\n'
    )
    r_s = apply_unique_replace(strings_path, old_s, new_s, "xaulinxs_restart_app_title", "3a (string)")

    # 3b) menu xml (arquivo novo — idempotente por existência)
    menu_dir = ROOT / "res" / "menu"
    menu_path = menu_dir / "xaulinxs_settings_menu.xml"
    if menu_path.exists() and "xaulinxs_action_restart_app" in read(menu_path):
        r_menu = "already"
    else:
        menu_dir.mkdir(parents=True, exist_ok=True)
        write(menu_path, (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<!--\n'
            '  XaulinXs Customizations — não faz parte do AOSP original.\n\n'
            '  Feature nova (info.txt): botão no canto superior, dentro da aba\n'
            '  principal de configurações, para reiniciar o app e aplicar\n'
            '  customizações que exigem reinício (ex.: fonte customizada global,\n'
            '  troca de wallpaper próprio, remoção de fundo dos ícones — mudanças\n'
            '  que dependem de recriação de processo/cache de ícones, não só da\n'
            '  Activity de Configurações).\n'
            '-->\n'
            '<menu xmlns:android="http://schemas.android.com/apk/res/android"\n'
            '    xmlns:app="http://schemas.android.com/apk/res-auto">\n\n'
            '    <item\n'
            '        android:id="@+id/xaulinxs_action_restart_app"\n'
            '        android:title="@string/xaulinxs_restart_app_title"\n'
            '        android:icon="@android:drawable/ic_menu_rotate"\n'
            '        app:showAsAction="ifRoom" />\n\n'
            '</menu>\n'
        ))
        r_menu = "applied"

    # 3c) XaulinXsAppRestarter.kt (arquivo novo)
    restarter_path = (ROOT / "modules" / "customizations" / "src" / "com" / "xaulinxs"
                       / "customizations" / "XaulinXsAppRestarter.kt")
    if restarter_path.exists() and "object XaulinXsAppRestarter" in read(restarter_path):
        r_restarter = "already"
    else:
        restarter_path.parent.mkdir(parents=True, exist_ok=True)
        write(restarter_path, '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Feature nova (info.txt): botão "Reiniciar para aplicar alterações" no
 * canto superior da aba principal de configurações.
 *
 * Por que Activity.recreate() (já existente via
 * SettingsActivity.LauncherSettingsFragment.tryRecreateActivity) NÃO é
 * suficiente aqui: várias customizações do XaulinXs dependem de estado
 * carregado uma única vez no PROCESSO (Application), não só na Activity
 * de Configurações — por exemplo, o Factory2 de fonte global instalado em
 * attachBaseContext de Launcher/SettingsActivity, o cache de bitmap de
 * ícones em BaseIconFactory (que decide na hora de gerar o bitmap se
 * remove ou não o fundo — bitmaps já gerados e cacheados não são
 * regenerados só por recriar uma Activity), e o wallpaper próprio
 * carregado por XaulinXsInAppWallpaper. recrear só a SettingsActivity não
 * reprocessa nada disso; é preciso matar e reabrir o processo inteiro.
 *
 * Abordagem padrão do Android para "reiniciar o app" (não existe API
 * pública de restart direto): agenda um PendingIntent que reabre a
 * Activity de entrada do launcher (mesma que o sistema usa para abrir o
 * home) via AlarmManager.set(), com um pequeno atraso, e então mata o
 * processo atual com Process.killProcess — o sistema recria o processo do
 * zero (nova instância de Application, novos Factory2, cache de ícones
 * limpo) quando o PendingIntent disparar.
 */
package com.xaulinxs.customizations

import android.app.Activity
import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Process
import android.os.SystemClock

object XaulinXsAppRestarter {

    private const val RESTART_DELAY_MILLIS = 300L

    @JvmStatic
    fun restart(activity: Activity) {
        val context = activity.applicationContext

        // Intent de reabertura: a própria launcher activity do app
        // (com.android.launcher3.Launcher), como uma abertura normal de
        // app — não usa Intent.ACTION_MAIN/CATEGORY_HOME para evitar
        // depender deste app já estar selecionado como launcher padrão
        // no momento do restart.
        val restartIntent = Intent(context, com.android.launcher3.Launcher::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }

        val pendingIntent = PendingIntent.getActivity(
            context,
            0,
            restartIntent,
            PendingIntent.FLAG_CANCEL_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        alarmManager.set(
            AlarmManager.ELAPSED_REALTIME,
            SystemClock.elapsedRealtime() + RESTART_DELAY_MILLIS,
            pendingIntent,
        )

        // Encerra o processo atual — o AlarmManager já agendado acima
        // garante a reabertura; não há "continuação" possível depois
        // desta chamada.
        Process.killProcess(Process.myPid())
    }
}
''')
        r_restarter = "applied"

    # 3d) SettingsActivity.java — 3 edições encadeadas
    sa_path = ROOT / "src" / "com" / "android" / "launcher3" / "settings" / "SettingsActivity.java"

    old_sa1 = (
        '    private static final int DELAY_HIGHLIGHT_DURATION_MILLIS = 600;\n'
        '    public static final String SAVE_HIGHLIGHTED_KEY = "android:preference_highlighted";\n'
        '\n'
        '    @Override\n'
        '    protected void attachBaseContext(Context base) {\n'
    )
    new_sa1 = (
        '    private static final int DELAY_HIGHLIGHT_DURATION_MILLIS = 600;\n'
        '    public static final String SAVE_HIGHLIGHTED_KEY = "android:preference_highlighted";\n'
        '\n'
        '    // XaulinXs Customizations: true quando esta instância da Activity é a\n'
        '    // tela PRINCIPAL de configurações (mesma condição já usada logo abaixo\n'
        '    // em onCreate para decidir se mostra a seta de voltar — quando nenhum\n'
        '    // desses extras está presente, a Activity foi aberta na raiz, não\n'
        '    // navegando para uma sub-tela específica).\n'
        '    private boolean mIsRootSettingsScreen;\n'
        '\n'
        '    @Override\n'
        '    protected void attachBaseContext(Context base) {\n'
    )

    old_sa2 = (
        '        Intent intent = getIntent();\n'
        '        if (intent.hasExtra(EXTRA_FRAGMENT_ROOT_KEY) || intent.hasExtra(EXTRA_FRAGMENT_ARGS)\n'
        '                || intent.hasExtra(EXTRA_FRAGMENT_HIGHLIGHT_KEY)) {\n'
        '            getActionBar().setDisplayHomeAsUpEnabled(true);\n'
        '        }\n'
    )
    new_sa2 = (
        '        Intent intent = getIntent();\n'
        '        boolean isSubScreen = intent.hasExtra(EXTRA_FRAGMENT_ROOT_KEY)\n'
        '                || intent.hasExtra(EXTRA_FRAGMENT_ARGS)\n'
        '                || intent.hasExtra(EXTRA_FRAGMENT_HIGHLIGHT_KEY);\n'
        '        if (isSubScreen) {\n'
        '            getActionBar().setDisplayHomeAsUpEnabled(true);\n'
        '        }\n'
        '        // XaulinXs Customizations: guarda se esta é a tela raiz — usado em\n'
        '        // onCreateOptionsMenu para só mostrar "Reiniciar para aplicar\n'
        '        // alterações" na aba principal, não em toda sub-tela de\n'
        '        // configuração aberta por cima dela.\n'
        '        mIsRootSettingsScreen = !isSubScreen;\n'
    )

    old_sa3 = (
        '    @Override\n'
        '    public boolean onOptionsItemSelected(MenuItem item) {\n'
        '        if (item.getItemId() == android.R.id.home) {\n'
        '            onBackPressed();\n'
        '            return true;\n'
        '        }\n'
        '        return super.onOptionsItemSelected(item);\n'
        '    }\n'
    )
    new_sa3 = (
        '    @Override\n'
        '    public boolean onCreateOptionsMenu(android.view.Menu menu) {\n'
        '        // XaulinXs Customizations (info.txt): botão no canto superior da\n'
        '        // aba principal de configurações, "Reiniciar para aplicar\n'
        '        // alterações" — necessário porque algumas customizações (fonte\n'
        '        // global, wallpaper próprio do launcher, remoção de fundo dos\n'
        '        // ícones) dependem de estado carregado uma única vez no processo\n'
        '        // (Application/cache de ícones), não só da Activity de\n'
        '        // Configurações — Activity.recreate() (já usado internamente por\n'
        '        // tryRecreateActivity) não é suficiente nesses casos. Só aparece\n'
        '        // na tela raiz (mIsRootSettingsScreen), não em toda sub-tela\n'
        '        // aberta por cima dela.\n'
        '        if (mIsRootSettingsScreen) {\n'
        '            getMenuInflater().inflate(R.menu.xaulinxs_settings_menu, menu);\n'
        '        }\n'
        '        return super.onCreateOptionsMenu(menu);\n'
        '    }\n'
        '\n'
        '    @Override\n'
        '    public boolean onOptionsItemSelected(MenuItem item) {\n'
        '        if (item.getItemId() == android.R.id.home) {\n'
        '            onBackPressed();\n'
        '            return true;\n'
        '        }\n'
        '        if (item.getItemId() == R.id.xaulinxs_action_restart_app) {\n'
        '            com.xaulinxs.customizations.XaulinXsAppRestarter.restart(this);\n'
        '            return true;\n'
        '        }\n'
        '        return super.onOptionsItemSelected(item);\n'
        '    }\n'
    )

    marker_sa = "mIsRootSettingsScreen"
    if sa_path.exists() and marker_sa in read(sa_path):
        r_sa = "already"
    else:
        text = read(sa_path) if sa_path.exists() else None
        if text is None:
            print(f"  [PULADO] 3d: {sa_path.relative_to(ROOT)} não encontrado")
            r_sa = "skipped-missing"
        elif text.count(old_sa1) != 1 or text.count(old_sa2) != 1 or text.count(old_sa3) != 1:
            print(f"  [PULADO] 3d: texto esperado não encontrado (ou duplicado) em "
                  f"{sa_path.relative_to(ROOT)} — provável edição manual anterior.")
            r_sa = "skipped-mismatch"
        else:
            text = text.replace(old_sa1, new_sa1, 1)
            text = text.replace(old_sa2, new_sa2, 1)
            text = text.replace(old_sa3, new_sa3, 1)
            write(sa_path, text)
            r_sa = "applied"

    results = {
        "string": r_s, "menu xml": r_menu,
        "XaulinXsAppRestarter.kt": r_restarter, "SettingsActivity.java": r_sa,
    }
    for label, r in results.items():
        tag = {"applied": "aplicado", "already": "já aplicado",
               "skipped-missing": "PULADO (arquivo ausente)",
               "skipped-mismatch": "PULADO (não bateu com o esperado)"}[r]
        print(f"  {label}: {tag}")


def main():
    fix_1_balloon_colors()
    print()
    fix_2_icon_background()
    print()
    fix_3_restart_button()
    print()
    print("Pronto. Rode de novo o build:")
    print("  ./gradlew assembleNoQuickstepDebug")


if __name__ == "__main__":
    main()
