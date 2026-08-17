#!/usr/bin/env python3
"""
Aplica o fix da regressão "nenhum widget funciona mais" causada pelo
patch da Fase 2 (fonte customizada global).

Causa raiz: Launcher.onCreate() passa "this" (a própria Activity
Launcher) como Context para LauncherWidgetHolder.newInstance(), que por
sua vez repassa para LauncherAppWidgetHost. Isso faz com que
AppWidgetHostView.updateAppWidget() / RemoteViews.apply() usem
LayoutInflater.from(context) do MESMO LayoutInflater da Activity — o
mesmo em que XaulinXsGlobalFontInflaterFactory foi instalado via
attachBaseContext(). RemoteViews.apply() já configura seu próprio
LayoutInflater.Filter nesse inflater compartilhado (a própria
RemoteViews implementa LayoutInflater.Filter, usado para restringir
quais views um widget de terceiro pode inflar por segurança) — o
Factory2 customizado rodando no meio desse fluxo quebra a inflação de
QUALQUER widget, nativo ou de terceiros.

Fix: XaulinXsGlobalFontInflaterFactory agora detecta se a view sendo
inflada está dentro de um AppWidgetHostView (checando o parent e todos
os ancestrais) e, se estiver, devolve null imediatamente — não aplica
fonte, não participa da resolução de classe, deixa o LayoutInflater
original (com o Filter do RemoteViews intacto) cuidar de tudo sozinho,
exatamente como se este Factory2 nem existisse para esse caso.

Não requer clonar: assume que o repo já existe em ~/Launcher3 (ou no
caminho passado via --repo) e aplica em cima do checkout local, para
não perder mudanças não commitadas.
"""
import argparse
import subprocess
import sys
from pathlib import Path

PATCH_FILENAME = "fix_widgets_regression.patch"

PATCH_CONTENT = '''diff --git a/modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsGlobalFontInflaterFactory.kt b/modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsGlobalFontInflaterFactory.kt
index 7c2c648..691ca28 100644
--- a/modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsGlobalFontInflaterFactory.kt
+++ b/modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsGlobalFontInflaterFactory.kt
@@ -24,6 +24,7 @@
  */
 package com.xaulinxs.customizations.font
 
+import android.appwidget.AppWidgetHostView
 import android.content.Context
 import android.util.AttributeSet
 import android.view.LayoutInflater
@@ -40,6 +41,27 @@ class XaulinXsGlobalFontInflaterFactory(
         context: Context,
         attrs: AttributeSet,
     ): View? {
+        // XaulinXs fix (causa raiz dos widgets quebrados na Fase 2): a
+        // Activity Launcher passa "this" como Context para
+        // LauncherWidgetHolder/LauncherAppWidgetHost, então
+        // AppWidgetHostView.updateAppWidget()/RemoteViews.apply() acaba
+        // usando LayoutInflater.from(context) do MESMO LayoutInflater da
+        // Activity — o que já tem este Factory2 instalado — em vez de um
+        // inflater isolado do processo do widget, como a suposição
+        // original (Fase 2) previa. RemoteViews.apply() já instala seu
+        // próprio LayoutInflater.Filter (a própria RemoteViews via
+        // onLoadClass) nesse mesmo inflater compartilhado para
+        // sandboxing de segurança — nosso Factory2 rodando no meio disso
+        // corrompe esse fluxo e quebra a inflação de QUALQUER widget.
+        // Fix: se algum ancestral na árvore de "parent" for um
+        // AppWidgetHostView, este Factory2 não participa em nada —
+        // devolve null imediatamente e deixa o LayoutInflater original
+        // resolver sozinho, do jeito que resolveria sem este Factory2
+        // existir.
+        if (isInsideAppWidgetHostView(parent)) {
+            return null
+        }
+
         // Deixa qualquer factory pré-existente (ex.: a própria do
         // PreferenceFragmentCompat/androidx) criar a view primeiro, se
         // houver uma; senão cai no inflater padrão da plataforma via
@@ -55,6 +77,15 @@ class XaulinXsGlobalFontInflaterFactory(
     override fun onCreateView(name: String, context: Context, attrs: AttributeSet): View? =
         onCreateView(null, name, context, attrs)
 
+    private fun isInsideAppWidgetHostView(parent: View?): Boolean {
+        var current = parent
+        while (current != null) {
+            if (current is AppWidgetHostView) return true
+            current = current.parent as? View
+        }
+        return false
+    }
+
     private fun createViewFallback(context: Context, name: String, attrs: AttributeSet): View? {
         // createView(name, prefix, attrs) resolve a classe via reflection
         // diretamente (Class.forName), SEM reconsultar nenhuma Factory —
'''


def run(cmd, cwd, check=True):
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, text=True)
    if check and result.returncode != 0:
        sys.exit(f"Comando falhou: {' '.join(cmd)}")
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        default=str(Path.home() / "Launcher3"),
        help="Caminho do checkout local (padrão: ~/Launcher3)",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Não rodar ./gradlew assembleDebug ao final",
    )
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_dir():
        sys.exit(f"Repo não encontrado em {repo}. Use --repo <caminho>.")

    target_file = (
        repo
        / "modules/customizations/src/com/xaulinxs/customizations/font"
        / "XaulinXsGlobalFontInflaterFactory.kt"
    )
    if not target_file.is_file():
        sys.exit(
            f"{target_file} não existe — este script espera que o patch "
            "da Fase 2 (fonte global) já esteja aplicado no checkout."
        )

    if "isInsideAppWidgetHostView" in target_file.read_text(encoding="utf-8"):
        print("Fix já aplicado neste checkout (idempotente) — nada a fazer.")
    else:
        patch_path = repo / PATCH_FILENAME
        patch_path.write_text(PATCH_CONTENT, encoding="utf-8")

        print("Conferindo se o patch aplica limpo (git apply --check)...")
        run(["git", "apply", "--check", PATCH_FILENAME], cwd=repo)

        print("Aplicando patch...")
        run(["git", "apply", PATCH_FILENAME], cwd=repo)

        patch_path.unlink()

        print("\nDiff aplicado:")
        run(["git", "diff", "--stat"], cwd=repo, check=False)
        run(
            [
                "git",
                "diff",
                "modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsGlobalFontInflaterFactory.kt",
            ],
            cwd=repo,
            check=False,
        )

    if not args.skip_build:
        print("\nCompilando (./gradlew assembleDebug)...")
        gradlew = repo / "gradlew"
        if not gradlew.is_file():
            sys.exit("gradlew não encontrado no repo — pulei o build.")
        run(["chmod", "+x", "gradlew"], cwd=repo)
        run(["./gradlew", "assembleDebug"], cwd=repo)
        print("\nBuild OK.")
    else:
        print("\n--skip-build: pulei a compilação.")

    print(
        "\nPróximo passo: instalar o APK debug e testar widgets na tela "
        "inicial (nativos e de terceiros) + confirmar que a fonte "
        "customizada continua aplicada fora dos widgets."
    )


if __name__ == "__main__":
    main()
