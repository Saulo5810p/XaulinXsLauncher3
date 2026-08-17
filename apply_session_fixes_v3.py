#!/usr/bin/env python3
"""
Aplica os 5 fixes do XaulinXsLauncher3 desta sessao, cada um de forma
INDEPENDENTE -- roda quantas vezes precisar, aplica so o que ainda
falta em cada arquivo, mesmo que alguns fixes ja tenham sido aplicados
em rodadas anteriores (v1/v2 deste script).

1) FONTE CUSTOM QUEBRANDO WIDGETS (XaulinXsGlobalFontInflaterFactory.kt)
   RemoteViews.apply() de qualquer widget reusa o LayoutInflater da
   Activity onde o Factory2 da fonte global foi instalado, quebrando a
   inflacao. Fix: Factory2 detecta AppWidgetHostView na arvore de
   parent e nao participa nesse caso.

2) QSB INVISIVEL EM DENSIDADE REAL (HotseatProfile.kt)
   qsbWidth era forcado a 0 em grids de telefone nao-escalaveis
   (isScalableGrid=false, o caso do Galaxy A35). Fix: calcula qsbWidth
   de verdade tambem nesse branch.

3) QSB LOCALIZAVA/BINDAVA WIDGET REAL DO GOOGLE (OseWidgetManager.kt)
   handleOseInfoUpdate() bindava um AppWidget de terceiro (RemoteViews
   real) do motor de busca padrao do sistema -- abria configuracoes do
   app Google no long-press e sofria o mesmo problema do item 1. Fix:
   nunca mais localiza/binda um AppWidget de terceiro -- sempre
   despacha valores nulos (providerInfo e views).

4) TITULOS SEM FONTE CUSTOMIZADA + CRASH AO ABRIR CONFIGURACOES
   (XaulinXsCustomFont.kt + SettingsActivity.java)
   O titulo da tela de Configuracoes e desenhado internamente por
   CollapsingToolbarLayout/Toolbar; o header "XaulinXs Customizations"
   e inflado por um LayoutInflater clonado -- nenhum dos dois e
   alcancado pelo Factory2 global. PRIMEIRA TENTATIVA deste fix
   chamava applyToPreferenceListRecycling(getListView()) dentro de
   onCreatePreferences(), mas getListView() so existe depois que
   PreferenceFragmentCompat.onCreateView() roda (posterior a
   onCreate()/onCreatePreferences() no ciclo de vida do Fragment) --
   retornava null e derrubava a Activity com NullPointerException ao
   abrir Configuracoes. Fix: chamada movida para onViewCreated(), onde
   a RecyclerView ja existe de verdade.

5) QSB FICOU ESTATICA/QUEBRADA VISUALMENTE APOS O FIX 3
   (OseWidgetView.kt)
   Com o fix 3, OseWidgetManager sempre despacha providerInfo=null e
   views=null. O codigo original de OseWidgetView.attachedToWindow()
   pressupoe que, apos providerInfo chegar, um evento real de "views"
   vem logo em seguida sobrescrevendo um RemoteViews(pkg, layoutId=0)
   usado so como placeholder de reset visual -- com tudo sempre null,
   esse RemoteViews vazio nunca e sobrescrito e fica permanentemente
   visivel, o que o framework renderiza como uma tela de erro nativa
   generica (nao a getErrorView() customizada do proprio launcher --
   essa so dispara quando updateAppWidget recebe null, nao um
   RemoteViews com layoutId=0). Fix: quando providerInfo chega null,
   pula o placeholder de reset e chama updateAppWidget(null)
   diretamente, o caminho que o framework ja trata corretamente
   (cai em getErrorView(): icone + label estatico + clique abre
   busca/browser).

Nao clona: assume que o repo ja existe localmente (padrao ~/Launcher3)
e aplica em cima do checkout, sem perder mudancas nao commitadas.
"""
import argparse
import subprocess
import sys
from pathlib import Path

FIXES = []


def _fix(relative_path, marker, patch_filename, patch_content):
    FIXES.append(
        {
            "path": relative_path,
            "marker": marker,
            "patch_filename": patch_filename,
            "patch_content": patch_content,
        }
    )


_fix(
    relative_path=(
        "modules/customizations/src/com/xaulinxs/customizations/font/"
        "XaulinXsGlobalFontInflaterFactory.kt"
    ),
    marker="isInsideAppWidgetHostView",
    patch_filename="fix_1_widgets.patch",
    patch_content=r'''
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
''')

_fix(
    relative_path="src/com/android/launcher3/deviceprofile/HotseatProfile.kt",
    marker="nonScalableQsbWidth",
    patch_filename="fix_2_qsb_visibility.patch",
    patch_content=r'''
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
''')

_fix(
    relative_path="src/com/android/launcher3/qsb/OseWidgetManager.kt",
    marker="nunca localiza/binda um AppWidget de terceiro",
    patch_filename="fix_3_ose_no_google_widget.patch",
    patch_content=r'''
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
''')

_fix(
    relative_path=(
        "modules/customizations/src/com/xaulinxs/customizations/font/"
        "XaulinXsCustomFont.kt"
    ),
    marker="applyToSettingsTitle",
    patch_filename="fix_4a_titles_font.patch",
    patch_content=r'''
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
''')

_fix(
    relative_path="src/com/android/launcher3/settings/SettingsActivity.java",
    marker="derrubava a Activity com NullPointerException",
    patch_filename="fix_4b_titles_and_crashfix.patch",
    patch_content=r'''
diff --git a/src/com/android/launcher3/settings/SettingsActivity.java b/src/com/android/launcher3/settings/SettingsActivity.java
index f2b1e61..bec06d8 100644
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
@@ -314,6 +338,20 @@ public class SettingsActivity extends FragmentActivity
         public void onViewCreated(View view, Bundle savedInstanceState) {
             super.onViewCreated(view, savedInstanceState);
             View listView = getListView();
+            // XaulinXs Customizations: aplica a fonte customizada no
+            // título/summary de cada linha da lista de preferences
+            // (inclusive "XaulinXs Customizations"), cobrindo também
+            // reciclagem de views durante o scroll — ver comentário em
+            // XaulinXsCustomFont.applyToPreferenceListRecycling.
+            // Precisa rodar aqui (onViewCreated), não em
+            // onCreatePreferences: a RecyclerView só existe depois que
+            // PreferenceFragmentCompat.onCreateView() roda, que é
+            // posterior a onCreate()/onCreatePreferences() no ciclo de
+            // vida do Fragment — getListView() ali retornava null e
+            // derrubava a Activity com NullPointerException.
+            com.xaulinxs.customizations.font.XaulinXsCustomFont
+                    .applyToPreferenceListRecycling(
+                            (androidx.recyclerview.widget.RecyclerView) listView);
             final int bottomPadding = listView.getPaddingBottom();
             listView.setOnApplyWindowInsetsListener((v, insets) -> {
                 v.setPadding(
''')

_fix(
    relative_path="src/com/android/launcher3/qsb/OseWidgetView.kt",
    marker="pula esse reset",
    patch_filename="fix_5_qsb_error_view.patch",
    patch_content=r'''
diff --git a/src/com/android/launcher3/qsb/OseWidgetView.kt b/src/com/android/launcher3/qsb/OseWidgetView.kt
index fd30810..6a34650 100644
--- a/src/com/android/launcher3/qsb/OseWidgetView.kt
+++ b/src/com/android/launcher3/qsb/OseWidgetView.kt
@@ -81,14 +81,38 @@ constructor(context: Context, attrs: AttributeSet? = null, defStyleAttr: Int = 0
     fun attachedToWindow() {
         closeActions.executeAllAndClear()
 
+        // XaulinXs Customizations: esta é a QSB nativa AOSP/Launcher3
+        // "NoQuickstep" — OseWidgetManager nunca mais localiza/binda um
+        // AppWidget de terceiro (ver comentário em
+        // OseWidgetManager.handleOseInfoUpdate), então providerInfo e
+        // views são sempre despachados como null. O fluxo original do
+        // AOSP abaixo pressupõe que, depois de setAppWidget(id, info)
+        // com um "info" real, um evento de "views" real chega logo em
+        // seguida sobrescrevendo o RemoteViews(context.packageName, 0)
+        // usado só como placeholder de reset — com info sempre null,
+        // esse RemoteViews vazio (layoutId=0) nunca é sobrescrito e
+        // fica permanentemente visível, o que o framework renderiza
+        // como uma UI de erro nativa genérica (não a nossa
+        // getErrorView() customizada — essa só dispara quando
+        // updateAppWidget recebe null, não um RemoteViews vazio).
+        // Fix: quando não há provider (it == null), pula esse reset
+        // por completo e delega direto para getErrorView(), chamando
+        // updateAppWidget(null) — o caminho que o framework já trata
+        // corretamente.
+        //
         // We use INVALID_APPWIDGET_ID because appWidgetId is not tracked in OseWidgetView. Instead
         // it is managed by OseWidgetManager and QsbAppWidgetHost.
         closeActions.add(
             oseWidgetManager.providerInfo.forEach(activityContext.uiExecutor) {
                 setAppWidget(INVALID_APPWIDGET_ID, it)
-                // We will get valid updateAppWidget remoteview call from OseWidgetManager again.
-                // This is only for resetting the remoteviews using a broken remote view.
-                updateAppWidget(RemoteViews(context.packageName, 0))
+                if (it == null) {
+                    updateAppWidget(null)
+                } else {
+                    // We will get valid updateAppWidget remoteview call from
+                    // OseWidgetManager again. This is only for resetting the
+                    // remoteviews using a broken remote view.
+                    updateAppWidget(RemoteViews(context.packageName, 0))
+                }
                 if (autoUpdateTag) tag = getTagInfo(it)
                 Log.i(TAG, "setAppWidget providerInfo=$it")
             }::close
''')


BUGGY_MARKER = (
    "src/com/android/launcher3/settings/SettingsActivity.java",
    "applyToPreferenceListRecycling(getListView())",
)


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

    buggy_path, buggy_marker = BUGGY_MARKER
    buggy_target = repo / buggy_path
    has_buggy_version = (
        buggy_target.is_file() and buggy_marker in buggy_target.read_text(encoding="utf-8")
    )

    applied_now = []
    already_applied = []
    failed = []

    for fix in FIXES:
        target = repo / fix["path"]
        if not target.is_file():
            print(f"AVISO: {target} nao existe neste checkout -- pulando este fix.")
            continue

        current_content = target.read_text(encoding="utf-8")

        if fix["marker"] in current_content:
            already_applied.append(fix["path"])
            continue

        # Caso especial: SettingsActivity.java tem a versao COM BUG do
        # fix anterior (chamava applyToPreferenceListRecycling dentro
        # de onCreatePreferences, causava o crash). O patch deste fix
        # (4b) foi gerado a partir do arquivo SEM nenhum fix de titulos
        # aplicado -- nao aplica limpo por cima da versao com bug.
        # Reverte esse arquivo especifico pro estado AOSP original
        # (git checkout) antes de aplicar o patch completo (titulos +
        # crash-fix juntos) -- nao afeta nenhum outro arquivo do repo.
        if fix["path"] == buggy_path and has_buggy_version:
            print(
                f"Versao com bug detectada em {buggy_path} -- revertendo "
                "esse arquivo para o estado original antes de reaplicar "
                "titulos + crash-fix juntos."
            )
            run(["git", "checkout", "--", buggy_path], cwd=repo)

        patch_path = repo / fix["patch_filename"]
        patch_path.write_text(fix["patch_content"], encoding="utf-8")

        check = subprocess.run(
            ["git", "apply", "--check", fix["patch_filename"]],
            cwd=repo,
            text=True,
            capture_output=True,
        )
        if check.returncode != 0:
            failed.append((fix["path"], check.stderr.strip()))
            patch_path.unlink()
            continue

        run(["git", "apply", fix["patch_filename"]], cwd=repo)
        patch_path.unlink()
        applied_now.append(fix["path"])

    print()
    if applied_now:
        print("Aplicados agora:")
        for p in applied_now:
            print(f"  + {p}")
    if already_applied:
        print("Ja estavam aplicados (idempotente, pulados):")
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
        print("\nNada a fazer -- todos os fixes disponiveis ja estao aplicados.")

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
        "  3) Long-press na QSB nao abre mais nenhuma tela de config de "
        "terceiro\n"
        "  4) QSB mostra icone de busca + clique abre browser (nao fica "
        "mais estatica/quebrada)\n"
        "  5) Abrir Configuracoes do launcher nao crasha mais\n"
        "  6) Fonte customizada aparece no titulo de Configuracoes e no "
        "header 'XaulinXs Customizations'"
    )


if __name__ == "__main__":
    main()
