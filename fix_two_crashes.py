#!/usr/bin/env python3
"""
Corrige os 2 crashes reportados pelo usuario, com stack trace real,
nesta ordem:

CRASH 1 -- UiThreadHelper / CalledFromWrongThreadException:
XaulinXsWidgetFontForcer.applyRecursively chamava TextView.setTypeface()
a partir de LauncherAppWidgetHostView.updateAppWidget(), mas esse
caminho as vezes roda fora da main thread -- o stack trace mostrou
AppWidgetHost.startListening() disparando de uma HandlerThread interna
("UiThreadHelper"). setTypeface() dispara requestLayout() internamente
(troca de fonte pode mudar as dimensoes do texto), e View exige que so
a thread que criou a hierarquia a toque. Fix: a aplicacao de fato agora
roda dentro de view.post {}, que sempre entrega na main thread mesmo se
a view ainda nao estiver anexada a janela nesse momento.

CRASH 2 -- NullPointerException ItemInfo.getViewId() ao rotacionar para
paisagem e scrollar as Settings:
WorkspaceLayoutManager.addInScreen fazia (ItemInfo) child.getTag() sem
checar null. Confirmado via git log que este arquivo NUNCA foi tocado
desde o import inicial do AOSP -- nao e regressao de nenhuma mudanca
deste projeto. O proprio codigo AOSP ja tem um log de diagnostico
proposital ("b/388022685") na funcao vizinha investigando exatamente
essa tag nula -- e um bug conhecido do upstream numa condicao de
corrida do rebind assincrono do model, sem fix oficial publico
conhecido. Fix: mesma defesa que o AOSP ja usa alguns paragrafos acima
para colisao de item -- loga e desiste de adicionar aquela view
especifica, em vez de deixar o NullPointerException derrubar a
Activity inteira.

Ambos os arquivos MODIFICADOS (patch via git apply, idempotente por marker):
  - modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsWidgetFontForcer.kt
  - src/com/android/launcher3/WorkspaceLayoutManager.java

Nao clona: assume que o repo ja existe localmente (padrao ~/Launcher3)
e aplica em cima do checkout, sem perder mudancas nao commitadas.
"""
import argparse
import subprocess
import sys
from pathlib import Path

PATCHES = [
    {
        "path": 'modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsWidgetFontForcer.kt',
        "marker": 'view.post {',
        "patch_content": 'diff --git a/modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsWidgetFontForcer.kt b/modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsWidgetFontForcer.kt\nindex 624aec5..e2afe76 100644\n--- a/modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsWidgetFontForcer.kt\n+++ b/modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsWidgetFontForcer.kt\n@@ -46,11 +46,34 @@ object XaulinXsWidgetFontForcer {\n      * aplicar null é seguro: reseta para o typeface original resolvido\n      * pelo tema/XML da própria view, mesmo comportamento de reset já\n      * usado em XaulinXsCustomFont.applyRecursively).\n+     *\n+     * XaulinXs fix (crash real confirmado via logcat do Galaxy A35):\n+     * updateAppWidget() -- de onde applyTo() é chamado -- às vezes roda\n+     * fora da main thread. O caminho observado no crash:\n+     * AppWidgetHost.startListening() (chamado a partir de uma\n+     * HandlerThread interna, "UiThreadHelper", não a main thread) ->\n+     * updateAppWidgetView() -> ListenableHostView.updateAppWidget() ->\n+     * LauncherAppWidgetHostView.updateAppWidget() ->\n+     * XaulinXsWidgetFontForcer.applyTo(). TextView.setTypeface()\n+     * dispara requestLayout() internamente (troca de fonte pode mudar\n+     * as dimensões do texto), e View exige que só a thread que criou a\n+     * hierarquia toque nela -- CalledFromWrongThreadException.\n+     * (XaulinXsWidgetBlur.applyTo(), chamado na linha logo acima desta\n+     * no host, nunca teve esse problema: setRenderEffect() só marca a\n+     * view para redesenho com efeito diferente, não invalida layout.)\n+     *\n+     * Fix: agenda a aplicação de fato via View.post(), que sempre\n+     * entrega o Runnable na main thread (mesmo se a view ainda não\n+     * estiver anexada à janela nesse momento -- o Android enfileira\n+     * internamente e despacha assim que anexa). applyTo() em si\n+     * continua podendo ser chamado de qualquer thread com segurança.\n      */\n     @JvmStatic\n     fun applyTo(view: View) {\n-        val typeface = XaulinXsCustomFont.loadTypefaceIfAvailable(view.context)\n-        applyRecursively(view, typeface)\n+        view.post {\n+            val typeface = XaulinXsCustomFont.loadTypefaceIfAvailable(view.context)\n+            applyRecursively(view, typeface)\n+        }\n     }\n \n     private fun applyRecursively(view: View, typeface: android.graphics.Typeface?) {\n',
    },
    {
        "path": 'src/com/android/launcher3/WorkspaceLayoutManager.java',
        "marker": 'addInScreen: child.getTag() is not an ItemInfo',
        "patch_content": 'diff --git a/src/com/android/launcher3/WorkspaceLayoutManager.java b/src/com/android/launcher3/WorkspaceLayoutManager.java\nindex e69faab..7b1fc48 100644\n--- a/src/com/android/launcher3/WorkspaceLayoutManager.java\n+++ b/src/com/android/launcher3/WorkspaceLayoutManager.java\n@@ -141,7 +141,26 @@ public interface WorkspaceLayoutManager {\n         }\n \n         // Get the canonical child id to uniquely represent this view in this screen\n-        ItemInfo info = (ItemInfo) child.getTag();\n+        //\n+        // XaulinXs fix (crash real confirmado via logcat do Galaxy A35 ao\n+        // rotacionar para paisagem e scrollar as Settings): em certas\n+        // condições de corrida do rebind assíncrono do model (ver o log\n+        // de diagnóstico "b/388022685" já deixado pelo próprio AOSP\n+        // acima, em addInScreenFromBind), child.getTag() chega null ou\n+        // sem ser um ItemInfo aqui -- bug preexistente do AOSP upstream,\n+        // não introduzido por nenhuma customização deste projeto (este\n+        // arquivo nunca foi tocado desde o import inicial). Sem um fix\n+        // oficial conhecido publicamente, a defesa segura é a mesma já\n+        // usada alguns parágrafos acima para colisão de item: logar e\n+        // desistir de adicionar ESTA view específica, em vez de deixar\n+        // o NullPointerException derrubar a Activity inteira.\n+        Object tag = child.getTag();\n+        if (!(tag instanceof ItemInfo)) {\n+            Log.e(TAG, "addInScreen: child.getTag() is not an ItemInfo (was: " + tag\n+                    + ") for view: " + child + " -- skipping add to avoid crash");\n+            return;\n+        }\n+        ItemInfo info = (ItemInfo) tag;\n         int childId = info.getViewId();\n \n         boolean markCellsAsOccupied = !(child instanceof Folder);\n',
    },
]

def run(cmd, cwd):
    result = subprocess.run(cmd, cwd=cwd, text=True)
    if result.returncode != 0:
        sys.exit(f"Comando falhou: {' '.join(cmd)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        default="~/Launcher3",
        help="Caminho do checkout local (padrao: ~/Launcher3)",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Nao rodar ./gradlew assembleNoQuickstepDebug ao final",
    )
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_dir():
        sys.exit(f"Repo nao encontrado em {repo}. Use --repo <caminho>.")

    applied_now = []
    already_applied = []
    failed = []

    for fix in PATCHES:
        target = repo / fix["path"]
        if not target.is_file():
            print(f"AVISO: {target} nao existe neste checkout -- pulando este fix.")
            continue

        current_content = target.read_text(encoding="utf-8")

        if fix["marker"] in current_content:
            already_applied.append(fix["path"])
            continue

        patch_filename = "_tmp_crash_fixes_patch.patch"
        patch_path = repo / patch_filename
        patch_path.write_text(fix["patch_content"], encoding="utf-8")

        check = subprocess.run(
            ["git", "apply", "--check", patch_filename],
            cwd=repo,
            text=True,
            capture_output=True,
        )
        if check.returncode != 0:
            failed.append((fix["path"], check.stderr.strip()))
            patch_path.unlink()
            continue

        run(["git", "apply", patch_filename], cwd=repo)
        patch_path.unlink()
        applied_now.append(fix["path"])

    print()
    if applied_now:
        print("Patches aplicados agora:")
        for p in applied_now:
            print(f"  + {p}")
    if already_applied:
        print("Patches ja estavam aplicados (idempotente, pulados):")
        for p in already_applied:
            print(f"  = {p}")
    if failed:
        print("NAO aplicados:")
        for p, err in failed:
            print(f"  ! {p}")
            last_line = err.splitlines()[-1] if err else "(sem detalhe)"
            print(f"    {last_line}")
        print(
            "\nPara os itens marcados com '!', descreva o que esta diferente "
            "nesse arquivo e eu gero um patch novo em cima do estado atual dele."
        )

    if not applied_now and not failed:
        print("\nNada a fazer -- tudo ja estava aplicado.")

    if not args.skip_build:
        print("\nCompilando (./gradlew assembleNoQuickstepDebug)...")
        gradlew = repo / "gradlew"
        if not gradlew.is_file():
            sys.exit("gradlew nao encontrado no repo -- pulei o build.")
        run(["chmod", "+x", "gradlew"], cwd=repo)
        run(["./gradlew", "assembleNoQuickstepDebug"], cwd=repo)
        print("\nBuild OK.")
    else:
        print("\n--skip-build: pulei a compilacao.")

    print(
        "\nProximo passo -- instalar o APK debug e testar:\n"
        "  1) Adicionar/remover widgets varias vezes seguidas, reiniciar o "
        "launcher (forcar 'startListening') -- nao deve mais crashar com "
        "CalledFromWrongThreadException\n"
        "  2) Rotacionar para paisagem e scrollar as Settings pra baixo "
        "varias vezes -- nao deve mais crashar com NullPointerException\n"
        "  3) Se o crash 2 ainda ocorrer em algum caso especifico, pegue o "
        "logcat daquele momento -- pode ser uma variante diferente da "
        "mesma condicao de corrida"
    )


if __name__ == "__main__":
    main()
