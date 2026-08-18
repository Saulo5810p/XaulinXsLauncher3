#!/usr/bin/env python3
"""
Corrige a causa raiz REAL dos widgets quebrados ("Nao e possivel
carregar o widget") e forca a fonte customizada tambem dentro de
widgets de terceiros (Calendar, Gmail, etc), nao so nos icones/telas
do proprio launcher.

DIAGNOSTICO (via logcat REAL do Galaxy A35, nao so leitura estatica
de codigo -- fixes anteriores desta linha de trabalho tentaram
resolver isso sem log real e nao funcionaram):

O fix 1 de uma sessao anterior (isInsideAppWidgetHostView, checando
ancestrais de View ja anexados) nunca funcionava de fato: durante a
inflacao (rInflateChildren), a view sendo criada ainda nao esta
anexada a nenhum AppWidgetHostView, entao esse ancestral nunca
existe no momento em que onCreateView roda -- o Factory2 global da
fonte participava da inflacao de QUALQUER widget do mesmo jeito.

O log real (widget do Calendar) mostrou a causa raiz verdadeira:
RemoteViews.inflateView() chama LayoutInflater.inflate() com o
Factory2 global instalado (visivel na propria stacktrace:
XaulinXsGlobalFontInflaterFactory.onCreateView -> createViewFallback).
createViewFallback usa um caminho de resolucao de classe mais
limitado (inflater.createView(name, prefix, attrs)) que o inflater
padrao -- ao construir a view raiz do widget, um atributo de tema
(actionBarTheme) acaba resolvendo um drawable-animator do PROPRIO
launcher (design_fab_hide_motion_spec) no contexto/classloader
ERRADO (pacote do widget de terceiro), causando
Resources$NotFoundException seguido de ClassNotFoundException ao
tentar inflar a tag <set> desse animator -- e derrubando a inflacao
inteira do widget.

FIX 1 (estabilidade): XaulinXsGlobalFontInflaterFactory.onCreateView
agora verifica context.packageName -- o Context REAL da inflacao,
nao um ancestral de View -- e nao participa em nada quando esse
pacote nao e o do proprio launcher (com.android.launcher3). Cobre
QUALQUER RemoteViews de QUALQUER app de terceiro, nao so quando ja
esta dentro de um AppWidgetHostView anexado.

FIX 2 (fonte forcada em widgets de terceiros, pedido explicito do
usuario mesmo sabendo que e mais invasivo): como nao ha hook de
inflacao seguro para widgets de terceiros (usar o Factory2 ali
reproduziria o mesmo bug do Fix 1), a fonte e aplicada via
pos-processamento na arvore de views JA INFLADA -- novo arquivo
XaulinXsWidgetFontForcer.kt, chamado de dentro de
LauncherAppWidgetHostView.updateAppWidget() (mesmo ponto de entrada
e mesmo padrao ja usado por XaulinXsWidgetBlur.applyTo), rodando a
cada atualizacao do widget -- o que tambem cobre o caso de um app
de terceiro reenviar um RemoteViews novo que reaplique o typeface
original: a proxima atualizacao do host reaplica a fonte de novo.

Arquivo NOVO (escrito direto, idempotente por conteudo):
  - modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsWidgetFontForcer.kt

Arquivos MODIFICADOS (patch via git apply, idempotente por marker):
  - modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsGlobalFontInflaterFactory.kt
  - src/com/android/launcher3/widget/LauncherAppWidgetHostView.java

Nao clona: assume que o repo ja existe localmente (padrao ~/Launcher3)
e aplica em cima do checkout, sem perder mudancas nao commitadas.
"""
import argparse
import subprocess
import sys
from pathlib import Path

NEW_FILES = {
    'modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsWidgetFontForcer.kt': '/*\n * XaulinXs Customizations — não faz parte do AOSP original.\n *\n * Força a fonte customizada também dentro de widgets de terceiros\n * (RemoteViews de outros apps: Calendar, Gmail, etc). Abordagem\n * deliberadamente diferente da usada para os ícones/telas do próprio\n * launcher (XaulinXsGlobalFontInflaterFactory, hook na INFLAÇÃO via\n * LayoutInflater.Factory2): widgets de terceiros usam o Context do\n * PACOTE DO WIDGET durante a inflação (ver\n * XaulinXsGlobalFontInflaterFactory — é exatamente por isso que esse\n * Factory2 agora ignora esses contextos, para não quebrar a inflação\n * deles), então não há hook de inflação seguro e genérico disponível\n * para widgets de terceiros sem repetir o mesmo bug de estabilidade.\n *\n * Estratégia: pós-processamento na árvore de views JÁ INFLADA, depois\n * que o widget termina de carregar — mesmo ponto de entrada e mesmo\n * padrão já usado por XaulinXsWidgetBlur (ver\n * LauncherAppWidgetHostView.updateAppWidget, chamado logo após\n * super.updateAppWidget). Percorre recursivamente a árvore da\n * AppWidgetHostView e troca o typeface de toda TextView (e subclasses:\n * Button, EditText, Chronometer, etc.) encontrada.\n *\n * Limitação conhecida e aceita: RemoteViews pode reaplicar estilos\n * originais (incluindo typeface) em atualizações futuras do widget\n * (ex.: o próprio app de terceiro reenviando um RemoteViews novo via\n * AppWidgetManager.updateAppWidget) — isso sobrescreveria a fonte\n * forçada até a próxima chamada de updateAppWidget() do host, que é\n * exatamente quando applyTo() roda de novo. Não há forma de interceptar\n * isso de forma mais imediata sem hooks mais invasivos (reflection em\n * RemoteViews.OnClickHandler/RemoteViews internals) — fora de escopo\n * por ora.\n */\npackage com.xaulinxs.customizations.font\n\nimport android.view.View\nimport android.view.ViewGroup\nimport android.widget.TextView\n\nobject XaulinXsWidgetFontForcer {\n\n    /**\n     * Percorre [view] (tipicamente a raiz de uma AppWidgetHostView) e\n     * aplica a fonte customizada configurada em toda TextView\n     * encontrada na árvore. Sem-op silencioso se nenhuma fonte estiver\n     * configurada (loadTypefaceIfAvailable retorna null nesse caso, e\n     * aplicar null é seguro: reseta para o typeface original resolvido\n     * pelo tema/XML da própria view, mesmo comportamento de reset já\n     * usado em XaulinXsCustomFont.applyRecursively).\n     */\n    @JvmStatic\n    fun applyTo(view: View) {\n        val typeface = XaulinXsCustomFont.loadTypefaceIfAvailable(view.context)\n        applyRecursively(view, typeface)\n    }\n\n    private fun applyRecursively(view: View, typeface: android.graphics.Typeface?) {\n        if (view is TextView) {\n            view.typeface = typeface\n        }\n        if (view is ViewGroup) {\n            for (i in 0 until view.childCount) {\n                applyRecursively(view.getChildAt(i), typeface)\n            }\n        }\n    }\n}\n',
}

PATCHES = [
    {
        "path": 'modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsGlobalFontInflaterFactory.kt',
        "marker": 'context.packageName != LAUNCHER_PACKAGE_NAME',
        "patch_content": 'diff --git a/modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsGlobalFontInflaterFactory.kt b/modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsGlobalFontInflaterFactory.kt\nindex 691ca28..bc41cdf 100644\n--- a/modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsGlobalFontInflaterFactory.kt\n+++ b/modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsGlobalFontInflaterFactory.kt\n@@ -24,7 +24,6 @@\n  */\n package com.xaulinxs.customizations.font\n \n-import android.appwidget.AppWidgetHostView\n import android.content.Context\n import android.util.AttributeSet\n import android.view.LayoutInflater\n@@ -41,24 +40,44 @@ class XaulinXsGlobalFontInflaterFactory(\n         context: Context,\n         attrs: AttributeSet,\n     ): View? {\n-        // XaulinXs fix (causa raiz dos widgets quebrados na Fase 2): a\n-        // Activity Launcher passa "this" como Context para\n-        // LauncherWidgetHolder/LauncherAppWidgetHost, então\n-        // AppWidgetHostView.updateAppWidget()/RemoteViews.apply() acaba\n-        // usando LayoutInflater.from(context) do MESMO LayoutInflater da\n-        // Activity — o que já tem este Factory2 instalado — em vez de um\n-        // inflater isolado do processo do widget, como a suposição\n-        // original (Fase 2) previa. RemoteViews.apply() já instala seu\n-        // próprio LayoutInflater.Filter (a própria RemoteViews via\n-        // onLoadClass) nesse mesmo inflater compartilhado para\n-        // sandboxing de segurança — nosso Factory2 rodando no meio disso\n-        // corrompe esse fluxo e quebra a inflação de QUALQUER widget.\n-        // Fix: se algum ancestral na árvore de "parent" for um\n-        // AppWidgetHostView, este Factory2 não participa em nada —\n-        // devolve null imediatamente e deixa o LayoutInflater original\n-        // resolver sozinho, do jeito que resolveria sem este Factory2\n-        // existir.\n-        if (isInsideAppWidgetHostView(parent)) {\n+        // XaulinXs fix v2 (causa raiz REAL confirmada via logcat real do\n+        // Galaxy A35, não só leitura estática de código — a hipótese\n+        // anterior, "não participar quando um ancestral já anexado é\n+        // AppWidgetHostView", nunca disparava: durante rInflateChildren()\n+        // a view sendo inflada ainda não está anexada a nenhum\n+        // AppWidgetHostView, então esse ancestral nunca existe no\n+        // momento em que onCreateView roda, e o Factory2 participava do\n+        // mesmo jeito.\n+        //\n+        // O log real mostrou: RemoteViews.inflateView() (widget do\n+        // Calendar, com.android.calendar:layout/appwidget) chama\n+        // LayoutInflater.inflate() com ESTE Factory2 instalado (visível\n+        // na stacktrace: XaulinXsGlobalFontInflaterFactory.onCreateView\n+        // -> createViewFallback). createViewFallback usa\n+        // inflater.createView(name, prefix, attrs), um caminho de\n+        // resolução mais limitado que o inflater padrão: ao construir a\n+        // view raiz do widget (LinearLayout), o construtor de View\n+        // resolve um atributo de tema (actionBarTheme) que aponta para\n+        // um drawable-animator do PRÓPRIO launcher\n+        // (design_fab_hide_motion_spec) só que resolvido no contexto/\n+        // classloader do pacote do Calendar -- Resources$NotFoundException\n+        // seguido de ClassNotFoundException ao tentar inflar a tag\n+        // <set> desse animator. Não é um problema de tag XML isolada; é\n+        // o contexto errado (tema do launcher vazando para dentro da\n+        // inflação de RemoteViews de outro pacote) sendo usado para\n+        // resolver um atributo de tema durante a construção da view.\n+        //\n+        // Fix real: nunca participar quando o Context da inflação não é\n+        // o do PRÓPRIO pacote do launcher. RemoteViews sempre infla\n+        // usando o Context do pacote do app dono do widget (Calendar,\n+        // Gmail, etc, nunca "com.android.launcher3") -- então essa\n+        // checagem cobre QUALQUER inflação de RemoteViews de QUALQUER\n+        // app de terceiro, não só quando está dentro de um\n+        // AppWidgetHostView já anexado. Também cobre, pelo mesmo\n+        // motivo, qualquer outro Context de pacote externo que por\n+        // ventura passe por este Factory2 (ex.: notificações\n+        // customizadas, outros usos de RemoteViews fora de widgets).\n+        if (context.packageName != LAUNCHER_PACKAGE_NAME) {\n             return null\n         }\n \n@@ -77,15 +96,6 @@ class XaulinXsGlobalFontInflaterFactory(\n     override fun onCreateView(name: String, context: Context, attrs: AttributeSet): View? =\n         onCreateView(null, name, context, attrs)\n \n-    private fun isInsideAppWidgetHostView(parent: View?): Boolean {\n-        var current = parent\n-        while (current != null) {\n-            if (current is AppWidgetHostView) return true\n-            current = current.parent as? View\n-        }\n-        return false\n-    }\n-\n     private fun createViewFallback(context: Context, name: String, attrs: AttributeSet): View? {\n         // createView(name, prefix, attrs) resolve a classe via reflection\n         // diretamente (Class.forName), SEM reconsultar nenhuma Factory —\n@@ -132,6 +142,14 @@ class XaulinXsGlobalFontInflaterFactory(\n     }\n \n     companion object {\n+        // O applicationId real do build (ver build.gradle:\n+        // applicationId "com.android.launcher3"). Hardcoded em vez de\n+        // BuildConfig.APPLICATION_ID porque BuildConfig ainda não é\n+        // usado em nenhum outro ponto deste módulo -- evita depender de\n+        // uma classe gerada cujo pacote pode variar conforme a variante\n+        // de build configurada no futuro.\n+        private const val LAUNCHER_PACKAGE_NAME = "com.android.launcher3"\n+\n         // Mesma ordem de prefixos que o PhoneLayoutInflater da plataforma\n         // tenta internamente ao resolver uma tag sem pacote.\n         private val PLATFORM_VIEW_PREFIXES = arrayOf(\n',
    },
    {
        "path": 'src/com/android/launcher3/widget/LauncherAppWidgetHostView.java',
        "marker": 'XaulinXsWidgetFontForcer.applyTo(this)',
        "patch_content": 'diff --git a/src/com/android/launcher3/widget/LauncherAppWidgetHostView.java b/src/com/android/launcher3/widget/LauncherAppWidgetHostView.java\nindex 979ea9d..d13520e 100644\n--- a/src/com/android/launcher3/widget/LauncherAppWidgetHostView.java\n+++ b/src/com/android/launcher3/widget/LauncherAppWidgetHostView.java\n@@ -164,6 +164,14 @@ public class LauncherAppWidgetHostView extends BaseLauncherAppWidgetHostView\n         // The provider info or the views might have changed.\n         checkIfAutoAdvance();\n         com.xaulinxs.customizations.blur.XaulinXsWidgetBlur.applyTo(this);\n+        // XaulinXs Customizations: força a fonte customizada também\n+        // dentro de widgets de terceiros (Calendar, Gmail, etc), não só\n+        // nos ícones/telas do próprio launcher. Roda a cada\n+        // updateAppWidget() (não só na primeira vez), o que também\n+        // cobre o caso de um app de terceiro reenviar um RemoteViews\n+        // novo que reaplique o typeface original — a próxima\n+        // atualização do host reaplica a fonte customizada de novo.\n+        com.xaulinxs.customizations.font.XaulinXsWidgetFontForcer.applyTo(this);\n     }\n \n     @Override\n',
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
        help="Nao rodar ./gradlew assembleDebug ao final",
    )
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_dir():
        sys.exit(f"Repo nao encontrado em {repo}. Use --repo <caminho>.")

    written_now = []
    already_written = []

    # --- Arquivos novos: escreve direto, idempotente por conteudo ---
    for rel_path, content in NEW_FILES.items():
        target = repo / rel_path
        if target.is_file() and target.read_text(encoding="utf-8") == content:
            already_written.append(rel_path)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written_now.append(rel_path)

    # --- Arquivos modificados: patch via git apply, idempotente por marker ---
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

        patch_filename = "_tmp_widget_font_fix_patch.patch"
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
    if written_now:
        print("Arquivos novos criados agora:")
        for p in written_now:
            print(f"  + {p}")
    if already_written:
        print("Arquivos novos ja existiam com o conteudo certo (idempotente, pulados):")
        for p in already_written:
            print(f"  = {p}")
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

    if not written_now and not applied_now and not failed:
        print("\nNada a fazer -- tudo ja estava aplicado.")

    if not args.skip_build:
        print("\nCompilando (./gradlew assembleDebug)...")
        gradlew = repo / "gradlew"
        if not gradlew.is_file():
            sys.exit("gradlew nao encontrado no repo -- pulei o build.")
        run(["chmod", "+x", "gradlew"], cwd=repo)
        run(["./gradlew", "assembleDebug"], cwd=repo)
        print("\nBuild OK.")
    else:
        print("\n--skip-build: pulei a compilacao.")

    print(
        "\nProximo passo -- instalar o APK debug e testar:\n"
        "  1) Adicionar o widget do Calendar (ou outro que quebrava antes) "
        "na home -- deve carregar normalmente, sem 'Nao e possivel carregar "
        "o widget'\n"
        "  2) Outros widgets de terceiros (Gmail, relogio, etc) tambem "
        "devem carregar normalmente\n"
        "  3) Texto DENTRO desses widgets de terceiros deve aparecer com a "
        "fonte customizada configurada (se houver uma configurada em "
        "XaulinXs Customizations)\n"
        "  4) Se algum widget especifico ainda quebrar, pegue o logcat "
        "daquele momento de novo -- pode ser uma causa diferente"
    )


if __name__ == "__main__":
    main()
