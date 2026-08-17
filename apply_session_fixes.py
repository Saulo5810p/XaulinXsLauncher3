#!/usr/bin/env python3
"""
Aplica os 4 fixes da sessao atual do XaulinXsLauncher3, em cima de um
checkout local (nao clona). Idempotente por arquivo: roda quantas vezes
precisar, so aplica o que ainda falta.

1) FONTE CUSTOM QUEBRANDO WIDGETS (XaulinXsGlobalFontInflaterFactory.kt)
   Causa: Launcher.onCreate() passa "this" (a propria Activity) como
   Context para LauncherWidgetHolder/LauncherAppWidgetHost, entao
   AppWidgetHostView.updateAppWidget()/RemoteViews.apply() reusam o
   MESMO LayoutInflater da Activity, onde o Factory2 da fonte global
   foi instalado via attachBaseContext(). RemoteViews.apply() ja
   instala seu proprio LayoutInflater.Filter nesse inflater
   compartilhado para sandboxing de seguranca -- o Factory2 rodando no
   meio disso quebrava a inflacao de QUALQUER widget.
   Fix: o Factory2 agora detecta se esta dentro de um AppWidgetHostView
   (sobe a arvore de parent) e devolve null imediatamente nesse caso,
   sem participar em nada.

2) QSB INVISIVEL EM DENSIDADE REAL (HotseatProfile.kt)
   Causa: Hotseat.onMeasure() mede a QSB com MeasureSpec.EXACTLY usando
   HotseatProfile.qsbWidth. O calculo desse campo tinha um branch
   "if (!isScalableGrid) return ...qsbWidth=0...". Nos grids de
   TELEFONE comuns (ex. "5_by_5"/Large Phone, o grid do Galaxy A35) o
   atributo isScalable nao e declarado em device_profiles.xml, entao
   usa o default false -- qsbWidth sempre zero, QSB nunca aparece.
   So grids de tablet/desktop tem isScalable=true. Forcar densidade
   774 fazia o algoritmo de "closest display option" escolher por
   acidente um grid de tablet, mascarando o bug.
   Fix: calcula qsbWidth de verdade tambem nesse branch, reaproveitando
   a funcao calculateQsbWidth() ja existente no arquivo -- sem ativar
   o algoritmo de scaling de grid escalavel (que mudaria tamanho de
   icones/padding do workspace inteiro).

3) QSB LIGADA AO WIDGET DE BUSCA DO GOOGLE (OseWidgetManager.kt)
   Causa: handleOseInfoUpdate() localizava e bindava um AppWidget REAL
   de terceiro (RemoteViews) do "on-device search engine" configurado
   no sistema -- no caso comum (Google como app padrao), isso injetava
   o widget de busca do Google na QSB. Consequencias: (a) long-press na
   QSB abria as configuracoes desse widget de terceiro via
   OseWidgetOptionsProvider/startConfigActivity; (b) a QSB ficava
   sujeita ao mesmo problema de RemoteViews.apply() do item 1.
   Fix: handleOseInfoUpdate() nunca mais localiza/binda um AppWidget de
   terceiro -- sempre despacha valores nulos, o que faz o framework
   (AppWidgetHostView.updateAppWidget(null)) cair automaticamente em
   OseWidgetView.getErrorView(), a UI estatica nativa do AOSP (icone +
   label + clique abre busca/browser), sem RemoteViews de terceiro e
   sem opcao de configuracao no long-press.

4) TITULOS SEM FONTE CUSTOMIZADA (XaulinXsCustomFont.kt +
   SettingsActivity.java)
   Causa: nem o titulo da tela de Configuracoes nem o header
   "XaulinXs Customizations" na lista de preferences sao alcancados
   pelo Factory2 global -- o primeiro e desenhado internamente por
   CollapsingToolbarLayout/Toolbar (nunca inflado como TextView via
   XML); o segundo e inflado por um LayoutInflater CLONADO
   (PreferenceFragmentCompat.onCreateView -> cloneInContext) que nem
   sempre carrega o mesmo Factory2.
   Fix: dois metodos novos em XaulinXsCustomFont -- applyToSettingsTitle()
   (chamado do onCreate de SettingsActivity, cobre CollapsingToolbarLayout
   e Toolbar simples) e applyToPreferenceListRecycling() (chamado do
   onCreatePreferences, usa OnChildAttachStateChangeListener na
   RecyclerView pra cobrir bind inicial e reciclagem durante scroll).

Nao clona: assume que o repo ja existe localmente (padrao ~/Launcher3)
e aplica em cima do checkout, para nao perder mudancas nao commitadas.
"""
import argparse
import subprocess
import sys
from pathlib import Path

PATCH_FILENAME = "fix_consolidado_sessao.patch"

PATCH_CONTENT = r'''
diff --git a/modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsCustomFont.kt b/modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsCustomFont.kt
index db4a0d5..5907e08 100644
--- a/modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsCustomFont.kt
+++ b/modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsCustomFont.kt
@@ -13,6 +13,7 @@ package com.xaulinxs.customizations.font
 import android.content.Context
 import android.graphics.Typeface
 import android.util.Log
+import android.widget.TextView
 import com.android.launcher3.ConstantItem
 import com.android.launcher3.EncryptionType
 import com.android.launcher3.LauncherPrefs
@@ -97,6 +98,87 @@ object XaulinXsCustomFont {
         }
     }
 
+    /**
+     * XaulinXs fix: o item "XaulinXs Customizations" na lista de
+     * preferences (título/summary de uma PreferenceScreen aninhada) não
+     * é alcançado de forma confiável por
+     * XaulinXsGlobalFontInflaterFactory — PreferenceFragmentCompat
+     * infla sua RecyclerView via um LayoutInflater CLONADO
+     * (inflater.cloneInContext), e o PreferenceGroupAdapter que
+     * desenha/recicla cada linha resolve o inflater a partir do Context
+     * do ViewGroup pai da RecyclerView, nem sempre o mesmo Factory2
+     * instalado em SettingsActivity.attachBaseContext.
+     *
+     * Fix: registra um listener na RecyclerView que aplica o typeface
+     * diretamente em título/summary de cada item anexado — cobre tanto
+     * o bind inicial quanto reciclagem durante scroll (diferente de uma
+     * aplicação única, que perderia os itens reciclados depois).
+     * Chamado do onCreatePreferences do fragment, depois que a
+     * RecyclerView já existe.
+     */
+    @JvmStatic
+    fun applyToPreferenceListRecycling(recyclerView: androidx.recyclerview.widget.RecyclerView) {
+        recyclerView.addOnChildAttachStateChangeListener(
+            object : androidx.recyclerview.widget.RecyclerView.OnChildAttachStateChangeListener {
+                override fun onChildViewAttachedToWindow(view: android.view.View) {
+                    val typeface = loadTypefaceIfAvailable(view.context)
+                    val title = view.findViewById<android.view.View>(android.R.id.title)
+                    if (title is TextView) title.typeface = typeface
+                    val summary = view.findViewById<android.view.View>(android.R.id.summary)
+                    if (summary is TextView) summary.typeface = typeface
+                }
+
+                override fun onChildViewDetachedFromWindow(view: android.view.View) = Unit
+            },
+        )
+    }
+
+    /**
+     * XaulinXs fix: o título da tela de Configurações não é alcançado
+     * por XaulinXsGlobalFontInflaterFactory porque nunca é inflado como
+     * TextView a partir de XML — é desenhado/gerenciado internamente
+     * pela própria Toolbar/CollapsingToolbarLayout. Chamado do onCreate
+     * de SettingsActivity, depois de setContentView()+setActionBar().
+     * Cobre os dois layouts possíveis (res/layout e res/layout-v31) sem
+     * reflection, usando só API pública de cada view.
+     */
+    @JvmStatic
+    fun applyToSettingsTitle(activity: android.app.Activity) {
+        val typeface = loadTypefaceIfAvailable(activity)
+
+        // Caso API 31+ (res/layout-v31/settings_activity.xml): o título
+        // é desenhado pelo CollapsingToolbarLayout, não pela Toolbar em
+        // si. Cobre título expandido e colapsado — são dois
+        // TextPaint/Typeface independentes na CollapsingTextHelper.
+        val collapsingToolbar = activity.findViewById<
+            com.google.android.material.appbar.CollapsingToolbarLayout>(
+            com.android.launcher3.R.id.collapsing_toolbar,
+        )
+        if (collapsingToolbar != null) {
+            val resolved = typeface ?: android.graphics.Typeface.DEFAULT
+            collapsingToolbar.setExpandedTitleTypeface(resolved)
+            collapsingToolbar.setCollapsedTitleTypeface(resolved)
+            return
+        }
+
+        // Caso pré-API 31 (res/layout/settings_activity.xml): Toolbar
+        // simples sem CollapsingToolbarLayout. Toolbar não expõe API
+        // pública de typeface do título, mas percorrer seus filhos
+        // diretos e achar a TextView é seguro e documentado como padrão
+        // (a própria Toolbar cria essa TextView internamente como filha
+        // direta quando setTitle() é chamado) — sem reflection.
+        val toolbar = activity.findViewById<android.widget.Toolbar>(
+            com.android.launcher3.R.id.action_bar,
+        ) ?: return
+        for (i in 0 until toolbar.childCount) {
+            val child = toolbar.getChildAt(i)
+            if (child is TextView && child.text == activity.title) {
+                child.typeface = typeface
+                break
+            }
+        }
+    }
+
     @JvmStatic
     fun loadTypefaceIfAvailable(context: Context): Typeface? {
         val path = getCustomFontPath(context)
diff --git a/modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsGlobalFontInflaterFactory.kt b/modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsGlobalFontInflaterFactory.kt
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
diff --git a/src/com/android/launcher3/deviceprofile/HotseatProfile.kt b/src/com/android/launcher3/deviceprofile/HotseatProfile.kt
index 78bc475..2bc4302 100644
--- a/src/com/android/launcher3/deviceprofile/HotseatProfile.kt
+++ b/src/com/android/launcher3/deviceprofile/HotseatProfile.kt
@@ -145,14 +145,58 @@ data class HotseatProfile(
             isVerticalBarLayout: Boolean,
             numShownHotseatIconsParam: Int,
         ): HotseatWithBorderAndSpace {
-            if (!isScalableGrid)
+            if (!isScalableGrid) {
+                // XaulinXs fix: no grid não-escalável (grid padrão de
+                // telefone, ex. "5_by_5"/Large Phone — o caso do
+                // Samsung Galaxy A35 em densidade real), este branch
+                // sempre zerava qsbWidth incondicionalmente. Hotseat
+                // mede a QSB com makeMeasureSpec(qsbWidth, EXACTLY), e
+                // largura exata 0 faz a QSB nunca aparecer — mesmo ela
+                // estando corretamente adicionada à hierarquia de views
+                // (addView(mQsb) sempre roda). Isso só não acontecia em
+                // densidades altas o bastante para o algoritmo de
+                // "closest display option" cair, por acidente, num
+                // GridOption com isScalable=true (ex. "6_by_5", grid de
+                // tablet) — não é um comportamento pretendido, é uma
+                // seleção de grid errada mascarando o bug.
+                // O próprio comentário de calculateQsbWidth() acima já
+                // documenta a intenção original: "QSB width is always
+                // calculated" — não deveria depender de isScalableGrid.
+                // Fix: calcula qsbWidth de verdade aqui também,
+                // reaproveitando calculateQsbWidth() com columnSpan =
+                // inv.numColumns (mesmo valor já usado para widthPx e
+                // columnSpan neste branch), sem alterar nada mais do
+                // comportamento do grid fixo de telefone (widthPx,
+                // borderSpace, numShownIcons continuam 0/inalterados —
+                // só qsbWidth passa a refletir a largura real).
+                val nonScalableQsbWidth =
+                    calculateQsbWidth(
+                        borderAndSpace =
+                            HotseatBorderAndSpace(
+                                widthPx = 0,
+                                columnSpan = inv.numColumns,
+                                borderSpace = 0,
+                            ),
+                        workspaceProfile = workspaceProfile,
+                        inv = inv,
+                        panelCount = panelCount,
+                        numShownHotseatIcons = numShownHotseatIconsParam,
+                        isQsbInline = hotseatProfileInitialValues.isQsbInline,
+                        // coerceAtLeast(0): MeasureSpec.EXACTLY com
+                        // largura negativa é comportamento indefinido —
+                        // salvaguarda defensiva, não deveria ocorrer em
+                        // grids de telefone normais, mas garante que
+                        // nunca voltamos a pior do que "QSB invisível"
+                        // (0px) em vez de crashar.
+                    ).coerceAtLeast(0)
                 return HotseatWithBorderAndSpace(
                     widthPx = 0,
                     numShownIcons = numShownHotseatIconsParam,
                     columnSpan = inv.numColumns,
-                    qsbWidth = 0,
+                    qsbWidth = nonScalableQsbWidth,
                     borderSpace = 0,
                 )
+            }
 
             var numShownHotseatIcons = numShownHotseatIconsParam
             var borderAndSpace =
diff --git a/src/com/android/launcher3/qsb/OseWidgetManager.kt b/src/com/android/launcher3/qsb/OseWidgetManager.kt
index a1925d8..dad0bcf 100644
--- a/src/com/android/launcher3/qsb/OseWidgetManager.kt
+++ b/src/com/android/launcher3/qsb/OseWidgetManager.kt
@@ -79,53 +79,34 @@ constructor(
         tracker.addCloseable { idp.removeOnChangeListener(idpListener) }
     }
 
-    private fun handleOseInfoUpdate(info: OSEInfo) {
-        // If the package is null, leave it to the current value as the OSEManager
-        // may not have initialized yet
-        val providerPkg =
-            if (info.pkg != null) {
-                info.pkg
-            } else {
-                // When defaultSearchPackage is disabled oseInfo pkg is null.
-                dispatchNullValues()
-                return
-            }
-        val searchWidget = findSearchWidgetForPackage(context, providerPkg)
-
+    private fun handleOseInfoUpdate(@Suppress("UNUSED_PARAMETER") info: OSEInfo) {
+        // XaulinXs Customizations: esta é a QSB nativa AOSP/Launcher3
+        // "NoQuickstep", não o Pixel Launcher com Widget de busca do
+        // Google. O comportamento AOSP original bindava um AppWidget
+        // real (RemoteViews de terceiro) do "on-device search engine"
+        // configurado no sistema — no caso comum (Google como app
+        // padrão), isso injetava o widget real de busca do Google na
+        // QSB, e por consequência: (1) o long-press na QSB abria as
+        // configurações desse widget de terceiro via
+        // OseWidgetOptionsProvider/startConfigActivity, e (2) a QSB
+        // ficava sujeita ao mesmo problema de RemoteViews.apply()
+        // reutilizando o LayoutInflater da Activity que afeta qualquer
+        // AppWidgetHostView (ver XaulinXsGlobalFontInflaterFactory).
+        // Fix: nunca localiza/binda um AppWidget de terceiro — sempre
+        // despacha valores nulos, o que faz o framework
+        // (AppWidgetHostView.updateAppWidget(null)) cair automaticamente
+        // em OseWidgetView.getErrorView(), a própria UI estática nativa
+        // do AOSP (ícone + label + clique abre busca/browser), sem
+        // nenhuma RemoteViews de terceiro envolvida e sem opção de
+        // configuração no long-press. widgetHost.getBoundWidgetId()
+        // permanece disponível para limpar qualquer widget já bindado
+        // de uma sessão anterior (antes deste fix).
         val currentWidgetId = widgetHost.getBoundWidgetId()
-        val currentInfo =
-            if (currentWidgetId != INVALID_APPWIDGET_ID)
-                AppWidgetManager.getInstance(context).getAppWidgetInfo(currentWidgetId)
-            else null
-
-        // Everything is in order
-        if (currentInfo?.provider == searchWidget?.provider) {
-            widgetHost.setActiveWidget(currentWidgetId, currentInfo)
-            updateWidgetSizeAsync()
-            return
-        }
-
-        // If there is no possible search widget, switch to a null view
-        if (searchWidget == null) {
-            widgetHost.setActiveWidget(INVALID_APPWIDGET_ID, null)
-            dispatchNullValues()
-            return
-        }
-
-        // Try to bind a new search widget
-        val widgetId = widgetHost.allocateAppWidgetId()
-        val bindSuccess =
-            AppWidgetManager.getInstance(context)
-                .bindAppWidgetIdIfAllowed(widgetId, searchWidget.provider)
-
-        if (bindSuccess) {
-            widgetHost.setActiveWidget(widgetId, searchWidget)
-            updateWidgetSizeAsync()
-        } else {
-            widgetHost.deleteAppWidgetId(widgetId)
-            widgetHost.setActiveWidget(INVALID_APPWIDGET_ID, null)
-            dispatchNullValues()
+        if (currentWidgetId != INVALID_APPWIDGET_ID) {
+            widgetHost.deleteAppWidgetId(currentWidgetId)
         }
+        widgetHost.setActiveWidget(INVALID_APPWIDGET_ID, null)
+        dispatchNullValues()
     }
 
     private fun updateWidgetSizeAsync() {
diff --git a/src/com/android/launcher3/settings/SettingsActivity.java b/src/com/android/launcher3/settings/SettingsActivity.java
index f2b1e61..1abc1df 100644
--- a/src/com/android/launcher3/settings/SettingsActivity.java
+++ b/src/com/android/launcher3/settings/SettingsActivity.java
@@ -108,6 +108,17 @@ public class SettingsActivity extends FragmentActivity
 
         setActionBar(findViewById(R.id.action_bar));
         WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
+        // XaulinXs Customizations: XaulinXsGlobalFontInflaterFactory não
+        // alcança o título desta tela porque ele nunca é inflado como
+        // TextView a partir de XML — em API 31+ (res/layout-v31, caso do
+        // Galaxy A35) é um CollapsingToolbarLayout que DESENHA o título
+        // internamente via CollapsingTextHelper (não infla view alguma
+        // para o texto); em versões anteriores é o próprio
+        // android.widget.Toolbar que cria sua TextView de título
+        // programaticamente, também fora do fluxo de LayoutInflater.
+        // Fix: aplica o typeface diretamente nos dois pontos possíveis,
+        // usando a API pública de cada view — sem reflection.
+        com.xaulinxs.customizations.font.XaulinXsCustomFont.applyToSettingsTitle(this);
 
         Intent intent = getIntent();
         if (intent.hasExtra(EXTRA_FRAGMENT_ROOT_KEY) || intent.hasExtra(EXTRA_FRAGMENT_ARGS)
@@ -137,6 +148,19 @@ public class SettingsActivity extends FragmentActivity
             // Display the fragment as the main content.
             fm.beginTransaction().replace(R.id.content_frame, f).commit();
         }
+
+        // XaulinXs Customizations: no layout pré-API 31 (sem
+        // CollapsingToolbarLayout), a TextView interna do título da
+        // Toolbar só é criada na primeira vez que setTitle() recebe um
+        // texto não vazio — o fragment acima ainda vai chamar
+        // getActivity().setTitle() de forma assíncrona ao montar as
+        // preferences, então a TextView pode não existir ainda no ponto
+        // acima. Reaplica depois que a fila de mensagens processar essa
+        // transação, garantindo que a TextView já exista. Sem efeito no
+        // caso CollapsingToolbarLayout (já resolvido acima, idempotente).
+        findViewById(R.id.content_frame).post(() ->
+                com.xaulinxs.customizations.font.XaulinXsCustomFont
+                        .applyToSettingsTitle(SettingsActivity.this));
     }
 
     private boolean startPreference(String fragment, Bundle args, String key) {
@@ -235,6 +259,14 @@ public class SettingsActivity extends FragmentActivity
             getPreferenceManager().setSharedPreferencesName(LauncherFiles.SHARED_PREFERENCES_KEY);
             setPreferencesFromResource(R.xml.launcher_preferences, rootKey);
 
+            // XaulinXs Customizations: aplica a fonte customizada no
+            // título/summary de cada linha da lista de preferences
+            // (inclusive "XaulinXs Customizations"), cobrindo também
+            // reciclagem de views durante o scroll — ver comentário em
+            // XaulinXsCustomFont.applyToPreferenceListRecycling.
+            com.xaulinxs.customizations.font.XaulinXsCustomFont
+                    .applyToPreferenceListRecycling(getListView());
+
             PreferenceScreen screen = getPreferenceScreen();
             for (int i = screen.getPreferenceCount() - 1; i >= 0; i--) {
                 Preference preference = screen.getPreference(i);
'''

# (arquivo, string-marcador que so existe depois do fix aplicado)
MARKERS = [
    (
        "modules/customizations/src/com/xaulinxs/customizations/font/"
        "XaulinXsGlobalFontInflaterFactory.kt",
        "isInsideAppWidgetHostView",
    ),
    (
        "src/com/android/launcher3/deviceprofile/HotseatProfile.kt",
        "nonScalableQsbWidth",
    ),
    (
        "src/com/android/launcher3/qsb/OseWidgetManager.kt",
        "nunca localiza/binda um AppWidget de terceiro",
    ),
    (
        "modules/customizations/src/com/xaulinxs/customizations/font/"
        "XaulinXsCustomFont.kt",
        "applyToSettingsTitle",
    ),
]


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

    already_applied = []
    for relative_path, marker in MARKERS:
        target = repo / relative_path
        if not target.is_file():
            sys.exit(f"{target} nao existe neste checkout.")
        if marker in target.read_text(encoding="utf-8"):
            already_applied.append(relative_path)

    if len(already_applied) == len(MARKERS):
        print("Todos os 4 fixes ja aplicados neste checkout (idempotente) -- nada a fazer.")
    elif already_applied:
        details = "\n".join(f"  - JA APLICADO: {p}" for p in already_applied)
        sys.exit(
            "Aplicacao parcial detectada neste checkout -- alguns fixes ja "
            "presentes, outros nao:\n"
            + details
            + "\nIsso normalmente significa que o patch consolidado nao "
            "aplica limpo em cima do estado atual. Aplique os patches "
            "individuais da sessao manualmente ou peca um novo patch "
            "consolidado a partir deste checkout."
        )
    else:
        patch_path = repo / PATCH_FILENAME
        patch_path.write_text(PATCH_CONTENT, encoding="utf-8")

        print("Conferindo se o patch aplica limpo (git apply --check)...")
        run(["git", "apply", "--check", PATCH_FILENAME], cwd=repo)

        print("Aplicando patch consolidado (4 fixes)...")
        run(["git", "apply", PATCH_FILENAME], cwd=repo)

        patch_path.unlink()

        print("\nDiff aplicado (resumo):")
        run(["git", "diff", "--stat"], cwd=repo, check=False)

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
        "\nProximo passo: instalar o APK debug e testar em DENSIDADE REAL "
        "(sem forcar dpi):\n"
        "  1) Widgets nativos e de terceiros voltam a funcionar\n"
        "  2) QSB aparece na dock, sem se sobrepor aos icones\n"
        "  3) Long-press na QSB nao abre mais config do widget do Google\n"
        "  4) Fonte customizada aparece no titulo de Configuracoes e no "
        "header 'XaulinXs Customizations'"
    )


if __name__ == "__main__":
    main()
