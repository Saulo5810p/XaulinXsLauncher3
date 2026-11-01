#!/usr/bin/env python3
"""
XaulinXsLauncher3 — 4 mudanças numa tacada só:

1) VÉU TEMÁTICO separado do desfoque do menu de apps
   - Nova preferência "Véu temático no menu de apps" (padrão: DESLIGADA).
   - As 3 manchas de cor do wallpaper (WallpaperGradientView) agora só
     aparecem se o véu estiver ligado. "Fundo desfocado no menu de apps"
     continua controlando apenas o desfoque.

2) DESIGN DA BARRA DE BUSCA (QSB da hotseat) no estilo QuickSearchBox do AOSP
   - Estrutura copiada do search_widget.xml da QuickSearchBox (Android 14):
     placa externa -> ícone de busca -> campo -> botão de voz (microfone).
   - Em vez de branca: 100% transparente por dentro, só as bordas brancas
     (estilo da barra do Android 4). Tudo em drawables XML, sem PNG.
   - O slider/seletor "Cor da barra" passa a colorir bordas + ícone + texto
     (padrão agora é branco).

3) DESFOQUE DA TELA INICIAL com o wallpaper próprio DESLIGADO
   - XaulinXsWallpaperView agora desfoca também a cópia do wallpaper do
     sistema usando o slider "Desfoque da tela inicial" (antes só valia
     para o wallpaper próprio do launcher).

4) NOVA PÁGINA "Sua Ideia..." (última página da Workspace)
   - Reconhecimento de voz nativo (SpeechRecognizer) + campo de texto.
   - Botões de microfone (iniciar) e pausa (parar). Texto salvo em disco e
     nunca apagado/resetado automaticamente.
   - Sem linhas visíveis; o limite de linhas é calculado pela altura real
     do retângulo (nada sai da área visível).
   - Interruptor em "R's Misc" (mesmo molde da página de música).

Rode na RAIZ do checkout (onde está o gradlew), no Termux:
    python3 apply_veil_qsb_homeblur_idea.py

Idempotente: se tudo já estiver aplicado, só avisa. Se algum trecho esperado
não for encontrado (arquivo diferente do GitHub), esse patch é pulado, o resto
continua e o script termina com código 1 listando os conflitos.
"""
import sys
from pathlib import Path

ROOT = Path(".")
CUST = "modules/customizations/src/com/xaulinxs/customizations"

errors: list = []


def write_new_file(path: Path, content: str) -> None:
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if current == content:
            print(f"[=] já aplicado, pulando: {path}")
            return
        errors.append(
            f"[!] CONFLITO: {path} já existe com conteúdo diferente do "
            f"esperado. Não sobrescrevi — verifique manualmente."
        )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"[+] criado: {path}")


def apply_patch(path: Path, old: str, new: str, label: str) -> None:
    if not path.exists():
        errors.append(f"[!] arquivo não encontrado: {path} (patch '{label}')")
        return
    text = path.read_text(encoding="utf-8")
    if new in text:
        print(f"[=] já aplicado, pulando: {label}")
        return
    if text.count(old) != 1:
        errors.append(
            f"[!] CONFLITO em {path} (patch '{label}'): trecho esperado "
            f"encontrado {text.count(old)}x (precisava de 1). O arquivo pode "
            f"ter mudado — verifique manualmente."
        )
        return
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"[+] patch aplicado: {label}")


# ===========================================================================
# 1) VÉU TEMÁTICO
# ===========================================================================
FILE_VEIL_PREF = ROOT / f"{CUST}/settings/ThemedVeilPreference.kt"
CONTENT_VEIL_PREF = r'''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Interruptor "Véu temático no menu de apps": liga/desliga as manchas de cor
 * do wallpaper (WallpaperGradientView) atrás do menu de apps. É INDEPENDENTE
 * do "Fundo desfocado no menu de apps" (ThemedScrimPreference): o desfoque
 * continua ligado/desligado por ele; as cores só aparecem se o usuário ligar
 * este interruptor. Desligado por padrão.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

class ThemedVeilPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(THEMED_VEIL_ENABLED)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(THEMED_VEIL_ENABLED, newValue as Boolean)
            true
        }
    }

    companion object {
        private const val KEY_THEMED_VEIL_ENABLED = "xaulinxs_themed_veil_enabled"
        val THEMED_VEIL_ENABLED = backedUpItem(KEY_THEMED_VEIL_ENABLED, false)
    }
}
'''

FILE_GRADIENT_VIEW = ROOT / f"{CUST}/theme/WallpaperGradientView.kt"

OLD_GV_IMPORT = "import com.xaulinxs.customizations.settings.ThemedScrimPreference.Companion.THEMED_SCRIM_ENABLED\n"
NEW_GV_IMPORT = (
    "import com.android.launcher3.LauncherPrefChangeListener\n"
    "import com.xaulinxs.customizations.settings.ThemedVeilPreference.Companion.THEMED_VEIL_ENABLED\n"
)

OLD_GV_FIELD = "    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)\n"
NEW_GV_FIELD = '''    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)

    // XAULINXS_THEMED_VEIL_SEPARATE: o véu (manchas de cor) agora tem interruptor próprio
    // (ThemedVeilPreference); redesenha na hora quando ele muda.
    private val veilPrefListener = object : LauncherPrefChangeListener {
        override fun onPrefChanged(key: String) {
            post { invalidate() }
        }
    }
'''

OLD_GV_ATTACH = '''        super.onAttachedToWindow()
        WallpaperColorHints.get(context).registerOnColorHintsChangedListener(this)
'''
NEW_GV_ATTACH = '''        super.onAttachedToWindow()
        WallpaperColorHints.get(context).registerOnColorHintsChangedListener(this)
        LauncherPrefs.get(context).addListener(veilPrefListener, THEMED_VEIL_ENABLED)
        invalidate()
'''

OLD_GV_DETACH = '''        super.onDetachedFromWindow()
        WallpaperColorHints.get(context).unregisterOnColorsChangedListener(this)
'''
NEW_GV_DETACH = '''        super.onDetachedFromWindow()
        WallpaperColorHints.get(context).unregisterOnColorsChangedListener(this)
        LauncherPrefs.get(context).removeListener(veilPrefListener, THEMED_VEIL_ENABLED)
'''

OLD_GV_GATE = "        if (!LauncherPrefs.get(context).get(THEMED_SCRIM_ENABLED)) return\n"
NEW_GV_GATE = (
    "        // XAULINXS_THEMED_VEIL_SEPARATE: só desenha as cores do véu se o usuário ativou o véu.\n"
    "        if (!LauncherPrefs.get(context).get(THEMED_VEIL_ENABLED)) return\n"
)

FILE_PREFS_XML = ROOT / "res/xml/launcher_preferences.xml"

OLD_PREFS_SCRIM = '''            <com.xaulinxs.customizations.settings.ThemedScrimPreference
                android:key="xaulinxs_themed_scrim"
                android:title="@string/xaulinxs_themed_scrim_title"
                android:summary="@string/xaulinxs_themed_scrim_summary"
                android:persistent="false" />
'''
NEW_PREFS_SCRIM = OLD_PREFS_SCRIM + '''
            <com.xaulinxs.customizations.settings.ThemedVeilPreference
                android:key="xaulinxs_themed_veil"
                android:title="@string/xaulinxs_themed_veil_title"
                android:summary="@string/xaulinxs_themed_veil_summary"
                android:persistent="false" />
'''

FILE_STRINGS = ROOT / "res/values/xaulinxs_strings.xml"

OLD_STR_SCRIM = '''    <string name="xaulinxs_themed_scrim_summary">Desfoca o papel de parede ao abrir/fechar o menu de apps, com o mesmo efeito de desfoque do arrasto</string>
'''
NEW_STR_SCRIM = OLD_STR_SCRIM + '''    <string name="xaulinxs_themed_veil_title">Véu temático no menu de apps</string>
    <string name="xaulinxs_themed_veil_summary">Mostra as cores do papel de parede (véu colorido) atrás do menu de apps. Independente do desfoque; desativado por padrão</string>
'''

# ===========================================================================
# 2) QSB — design QuickSearchBox transparente
# ===========================================================================
FILE_QSB_BG = ROOT / "res/drawable/xaulinxs_qsb_quicksearchbox_bg.xml"
CONTENT_QSB_BG = '''<?xml version="1.0" encoding="utf-8"?>
<!--
  XaulinXs Customizations — não faz parte do AOSP original.

  Design da barra de busca no estilo da QuickSearchBox do AOSP (search_widget.xml):
      [ placa externa ]  ->  [ ícone de busca ] [ campo ] [ botão de voz com microfone ]
  Em vez da placa branca do original: 100% transparente por dentro, só as bordas
  brancas (estilo da barra do Android 4). Branco puro de propósito — o app tinge
  tudo via backgroundTintList com "Cor da barra" (QsbConfig.BAR_COLOR).

  Medidas conferem com ose_default_bubbletext_layout.xml: ícone 24dp começando em 12dp,
  texto começando em 54dp (dentro do campo, que começa em 44dp), 72dp livres no fim.
-->
<ripple xmlns:android="http://schemas.android.com/apk/res/android"
    android:color="?android:attr/colorControlHighlight">

    <item android:id="@android:id/mask">
        <shape android:shape="rectangle">
            <corners android:radius="12dp" />
            <solid android:color="#FFFFFFFF" />
        </shape>
    </item>

    <item>
        <layer-list>

            <!-- Placa externa (search_floater) -->
            <item>
                <shape android:shape="rectangle">
                    <corners android:radius="12dp" />
                    <solid android:color="#00FFFFFF" />
                    <stroke android:width="2dp" android:color="#FFFFFFFF" />
                </shape>
            </item>

            <!-- Campo de texto (textfield_search_empty) -->
            <item
                android:left="44dp"
                android:top="7dp"
                android:right="62dp"
                android:bottom="7dp">
                <shape android:shape="rectangle">
                    <corners android:radius="8dp" />
                    <solid android:color="#00FFFFFF" />
                    <stroke android:width="1dp" android:color="#99FFFFFF" />
                </shape>
            </item>

            <!-- Botão de voz (btn_search_dialog_voice) -->
            <item
                android:gravity="end|center_vertical"
                android:width="44dp"
                android:height="38dp"
                android:right="8dp">
                <shape android:shape="rectangle">
                    <corners android:radius="8dp" />
                    <solid android:color="#00FFFFFF" />
                    <stroke android:width="1dp" android:color="#99FFFFFF" />
                </shape>
            </item>

            <!-- Microfone (ic_btn_speak_now) centralizado no botão de voz -->
            <item
                android:gravity="end|center_vertical"
                android:width="22dp"
                android:height="22dp"
                android:right="19dp"
                android:drawable="@drawable/ic_xaulinxs_qsb_mic" />

        </layer-list>
    </item>
</ripple>
'''

FILE_QSB_MIC = ROOT / "res/drawable/ic_xaulinxs_qsb_mic.xml"
CONTENT_QSB_MIC = '''<?xml version="1.0" encoding="utf-8"?>
<!-- XaulinXs Customizations — microfone (Material) do botão de voz da QSB. -->
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M12,14c1.66,0 2.99,-1.34 2.99,-3L15,5c0,-1.66 -1.34,-3 -3,-3S9,3.34 9,5v6c0,1.66 1.34,3 3,3zM17.3,11c0,3 -2.54,5.1 -5.3,5.1S6.7,14 6.7,11L5,11c0,3.41 2.72,6.23 6,6.72L11,21h2v-3.28c3.28,-0.48 6,-3.3 6,-6.72h-1.7z" />
</vector>
'''

FILE_QSB_LAYOUT = ROOT / "res/layout/ose_default_bubbletext_layout.xml"

OLD_QSB_PAD = '''    android:paddingStart="16dp"
    android:paddingEnd="16dp"
    android:drawablePadding="@dimen/qsb_search_icon_padding_end"
'''
NEW_QSB_PAD = '''    android:paddingStart="12dp"
    android:paddingEnd="72dp"
    android:drawablePadding="18dp"
    app:iconSizeOverride="24dp"
'''

OLD_QSB_BG = '''    android:background="@drawable/bg_ose_default"
    android:backgroundTint="@color/materialColorSurfaceContainerLow" />'''
NEW_QSB_BG = '''    android:textColor="#FFFFFFFF"
    android:background="@drawable/xaulinxs_qsb_quicksearchbox_bg" />'''

FILE_OSE_VIEW = ROOT / "src/com/android/launcher3/qsb/OseWidgetView.kt"

OLD_OSE_LISTENER = '''        val prefs = com.android.launcher3.LauncherPrefs.get(context)
        val qsbAppearanceListener =
            object : com.android.launcher3.LauncherPrefChangeListener {
                override fun onPrefChanged(key: String) {
                    applyXaulinXsQsbAppearance(view)
                }
            }
'''
NEW_OSE_LISTENER = '''        val prefs = com.android.launcher3.LauncherPrefs.get(context)
        // XAULINXS_QSB_QUICKSEARCHBOX_DESIGN: "Cor da barra" agora também colore o ícone de
        // busca (além de bordas e texto); quem refaz o ícone é o updateListener abaixo.
        var refreshQsbIcon: (() -> Unit)? = null
        val qsbAppearanceListener =
            object : com.android.launcher3.LauncherPrefChangeListener {
                override fun onPrefChanged(key: String) {
                    applyXaulinXsQsbAppearance(view)
                    refreshQsbIcon?.invoke()
                }
            }
'''

OLD_OSE_TINT = "                            setTint(context.getColor(R.color.materialColorOnSurface))\n"
NEW_OSE_TINT = "                            setTint(QsbConfig.getBarColor(context))\n"

OLD_OSE_REFRESH = '''        updateListener.onAppsUpdated()
        view.registerLifecycleTask {
            appsStore.addUpdateListener(updateListener)
'''
NEW_OSE_REFRESH = '''        updateListener.onAppsUpdated()
        refreshQsbIcon = { updateListener.onAppsUpdated() }
        view.registerLifecycleTask {
            appsStore.addUpdateListener(updateListener)
'''

OLD_OSE_APPEARANCE = "        view.backgroundTintList = ColorStateList.valueOf(QsbConfig.getBarColor(context))\n"
NEW_OSE_APPEARANCE = '''        // XAULINXS_QSB_QUICKSEARCHBOX_DESIGN: o fundo agora é só borda branca (placa/campo/botão de
        // voz, ver xaulinxs_qsb_quicksearchbox_bg.xml) — a cor escolhida tinge bordas, microfone e
        // texto; o interior continua 100% transparente (SRC_IN preserva o alpha do desenho).
        val barColor = QsbConfig.getBarColor(context)
        view.backgroundTintList = ColorStateList.valueOf(barColor)
        view.setTextColor(barColor)
'''

FILE_QSB_CONFIG = ROOT / f"{CUST}/qsb/QsbConfig.kt"
OLD_QSB_DEFAULT = '''    // Mesmo roxo Material usado como default em XaulinXsManualColor, por
    // consistência visual entre as duas telas de personalização.
    private const val DEFAULT_BAR_COLOR = 0xFF6750A4.toInt()
'''
NEW_QSB_DEFAULT = '''    // XAULINXS_QSB_QUICKSEARCHBOX_DESIGN: a barra agora é transparente com bordas
    // brancas (estilo QuickSearchBox/Android 4); a "Cor da barra" tinge bordas, ícone
    // e texto, então o padrão é branco (antes era o roxo Material do fundo sólido).
    private const val DEFAULT_BAR_COLOR = 0xFFFFFFFF.toInt()
'''

OLD_STR_QSB_COLOR = '<string name="xaulinxs_qsb_config_color_label">Cor da barra</string>'
NEW_STR_QSB_COLOR = '<string name="xaulinxs_qsb_config_color_label">Cor da barra (bordas, ícone e texto)</string>'

# ===========================================================================
# 3) Desfoque da tela inicial com wallpaper próprio desligado
# ===========================================================================
FILE_WALLPAPER_VIEW = ROOT / f"{CUST}/theme/XaulinXsWallpaperView.kt"

OLD_WV_PREFCHANGED = "    private val onBlurPrefChanged: () -> Unit = { post { applyBlurEffect() } }\n"
NEW_WV_PREFCHANGED = '''    private val onBlurPrefChanged: () -> Unit =
        { post { applyBlurEffect(); preloadSystemWallpaperIfNeeded(); invalidate() } }
'''

OLD_WV_APPLY = '''        // XAULINXS_BLUR_V3: com o wallpaper do app desligado, o desfoque do drawer continua valendo —
        // aplicado à cópia do wallpaper do sistema (ver onDraw). O desfoque fixo da tela inicial
        // segue valendo só para o wallpaper do app.
        val radiusPx = if (isInAppWallpaperEnabled()) {
            maxOf(XaulinXsWorkspaceBlur.getBlurRadiusPx(context), depthBlurRadiusPx)
        } else {
            depthBlurRadiusPx
        }
'''
NEW_WV_APPLY = '''        // XAULINXS_HOME_BLUR_SYSTEM_WALLPAPER: com o wallpaper do app desligado, tanto o desfoque
        // do drawer quanto o desfoque FIXO da tela inicial passam a valer — ambos aplicados à
        // cópia do wallpaper do sistema (ver drawSystemWallpaperSnapshot). Antes o desfoque da
        // tela inicial só valia para o wallpaper do app.
        val radiusPx = maxOf(XaulinXsWorkspaceBlur.getBlurRadiusPx(context), depthBlurRadiusPx)
'''

OLD_WV_PRELOAD = "        if (!prefs.get(THEMED_SCRIM_ENABLED) && !XaulinXsPopupBlur.isEnabled(context)) return\n"
NEW_WV_PRELOAD = '''        // XAULINXS_HOME_BLUR_SYSTEM_WALLPAPER: o desfoque da tela inicial também precisa da cópia.
        if (!prefs.get(THEMED_SCRIM_ENABLED) &&
            !XaulinXsPopupBlur.isEnabled(context) &&
            XaulinXsWorkspaceBlur.getBlurRadiusPx(context) <= 0f
        ) return
'''

OLD_WV_RADIUS = '''        val radius = depthBlurRadiusPx
        if (radius < 1f) return
        val bitmap = XaulinXsSystemWallpaperSnapshot.peek() ?: return
'''
NEW_WV_RADIUS = '''        // XAULINXS_HOME_BLUR_SYSTEM_WALLPAPER: raio efetivo = maior entre o desfoque fixo da tela
        // inicial e o do arrasto do drawer (mesma regra de applyBlurEffect).
        val workspaceRadius = XaulinXsWorkspaceBlur.getBlurRadiusPx(context)
        val radius = maxOf(workspaceRadius, depthBlurRadiusPx)
        if (radius < 1f) return
        val bitmap = XaulinXsSystemWallpaperSnapshot.peek() ?: return
'''

OLD_WV_ALPHA = "        systemPaint.alpha = (255f * (radius / SNAPSHOT_FADE_IN_PX).coerceIn(0f, 1f)).toInt()\n"
NEW_WV_ALPHA = '''        // Desfoque fixo da tela inicial: cópia sempre opaca (não há transição a esconder). Só o
        // arrasto do drawer usa o fade-in por raio.
        systemPaint.alpha = if (workspaceRadius >= 1f) {
            255
        } else {
            (255f * (radius / SNAPSHOT_FADE_IN_PX).coerceIn(0f, 1f)).toInt()
        }
'''

# ===========================================================================
# 4) Página "Sua Ideia..."
# ===========================================================================
FILE_IDEA_VIEW = ROOT / f"{CUST}/misc/idea/XaulinXsIdeaPageView.kt"
CONTENT_IDEA_VIEW = r'''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Página fixa "Sua Ideia...": ÚLTIMA página da Workspace (ver
 * Workspace.xaulinXsInsertIdeaPageIfEnabled), ocupando a grade inteira — por
 * isso nada pode ser solto nela, mesmo esquema da página de música.
 *
 * - Ditado: SpeechRecognizer nativo do Android. Botão de microfone inicia, botão
 *   de pausa para. A gravação é contínua: quando o reconhecedor encerra sozinho
 *   (silêncio), uma nova sessão começa até o usuário apertar pausa.
 * - O texto da ideia NUNCA é apagado nem resetado pelo app: é salvo a cada
 *   alteração (XaulinXsIdeaStore) e só muda quando o usuário edita o campo
 *   (teclado) ou dita mais texto (que é ANEXADO ao final).
 * - Sem linhas visíveis. O limite de linhas é calculado pela altura REAL do
 *   retângulo (StaticLayout com o mesmo paint/largura do EditText): digitação,
 *   colagem e ditado não passam do que cabe, então nada sai da área visível.
 * - Digitar no teclado durante a gravação pausa a gravação (evita o ditado
 *   sobrescrever o que foi digitado). Sair da página (rolar para outra, tela
 *   apagar) também para o microfone.
 */
package com.xaulinxs.customizations.misc.idea

import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.text.Editable
import android.text.InputType
import android.text.Layout
import android.text.StaticLayout
import android.text.TextWatcher
import android.view.Gravity
import android.view.ViewGroup
import android.view.ViewTreeObserver
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.widget.EditText
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import com.android.launcher3.LauncherSettings
import com.android.launcher3.model.data.ItemInfo
import com.xaulinxs.customizations.misc.XaulinXsMiscPermissionActivity
import com.xaulinxs.customizations.misc.XaulinXsMiscPermissions
import com.xaulinxs.customizations.misc.XaulinXsMiscSettings
import java.util.Locale

private const val PAGE_TITLE = "Sua Ideia..."
private const val STATUS_IDLE = "Digite ou toque no microfone para falar"
private const val STATUS_LISTENING = "Ouvindo… fale agora"
private const val STATUS_PAUSED = "Gravação pausada"
private const val STATUS_FULL = "Espaço de linhas esgotado — o texto não cabe mais"
private const val STATUS_DENIED = "Permissão do microfone negada"
private const val STATUS_UNAVAILABLE = "Reconhecimento de voz indisponível neste aparelho"
private const val STATUS_NETWORK = "Reconhecimento indisponível (rede/servidor do ditado)"
private const val STATUS_ERROR = "Não foi possível usar o microfone"

private const val MAX_CONSECUTIVE_ERRORS = 3
private const val MATCH = ViewGroup.LayoutParams.MATCH_PARENT
private const val WRAP = ViewGroup.LayoutParams.WRAP_CONTENT

/** Persistência do texto da ideia (arquivo de preferências próprio, nunca limpo pelo app). */
internal object XaulinXsIdeaStore {
    private const val PREFS = "xaulinxs_idea_page"
    private const val KEY_TEXT = "text"

    fun load(context: Context): String =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_TEXT, "").orEmpty()

    fun save(context: Context, text: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY_TEXT, text).apply()
    }
}

class XaulinXsIdeaPageView(context: Context) : LinearLayout(context) {

    private val density = resources.displayMetrics.density
    private val main = Handler(Looper.getMainLooper())

    private val input = EditText(context)
    private val statusView = TextView(context)
    private val micButton = ImageButton(context)
    private val pauseButton = ImageButton(context)

    // Estado do texto
    private var programmatic = false
    private var lastGoodText = ""

    // Estado do ditado
    private var recognizer: SpeechRecognizer? = null
    private var wantListening = false       // usuário pediu gravação (vale até apertar pausa)
    private var sessionActive = false       // há uma sessão do SpeechRecognizer rodando
    private var acceptResults = false       // resultados ainda podem entrar no campo
    private var baseText = ""               // texto do campo no início da sessão atual
    private var consecutiveErrors = 0
    private var pendingStartAfterPermission = false

    private val screenLoc = IntArray(2)

    private val restartRunnable = Runnable {
        if (wantListening && !sessionActive) beginSession()
    }
    private val stopAcceptRunnable = Runnable {
        if (!wantListening) acceptResults = false
    }
    private val permissionListener = Runnable { onPermissionResult() }
    private val scrollListener = ViewTreeObserver.OnScrollChangedListener { onPageMoved() }

    private val recognitionListener = object : RecognitionListener {
        override fun onReadyForSpeech(params: Bundle?) {
            if (wantListening) statusView.text = STATUS_LISTENING
        }

        override fun onBeginningOfSpeech() {}

        override fun onRmsChanged(rmsdB: Float) {}

        override fun onBufferReceived(buffer: ByteArray?) {}

        override fun onEndOfSpeech() {}

        override fun onError(error: Int) {
            sessionActive = false
            handleError(error)
        }

        override fun onResults(results: Bundle?) {
            sessionActive = false
            val best = firstResult(results)
            if (acceptResults && best.isNotBlank()) {
                consecutiveErrors = 0
                applySpeech(best)
            }
            if (wantListening) scheduleRestart(250) else acceptResults = false
        }

        override fun onPartialResults(partialResults: Bundle?) {
            val best = firstResult(partialResults)
            if (acceptResults && best.isNotBlank()) applySpeech(best)
        }

        override fun onEvent(eventType: Int, params: Bundle?) {}
    }

    init {
        orientation = VERTICAL
        super.setPadding(dp(16), dp(16), dp(16), dp(16))

        val title = TextView(context).apply {
            text = PAGE_TITLE
            setTextColor(Color.WHITE)
            textSize = 22f
            setTypeface(typeface, Typeface.BOLD)
            setShadowLayer(dp(3).toFloat(), 0f, dp(1).toFloat(), 0x99000000.toInt())
        }
        addView(title, LayoutParams(MATCH, WRAP).apply { bottomMargin = dp(12) })

        configureInput()
        addView(input, LayoutParams(MATCH, 0, 1f))

        statusView.apply {
            text = STATUS_IDLE
            setTextColor(Color.WHITE)
            textSize = 14f
            gravity = Gravity.CENTER
            setShadowLayer(dp(3).toFloat(), 0f, dp(1).toFloat(), 0x99000000.toInt())
        }
        addView(statusView, LayoutParams(MATCH, WRAP).apply { topMargin = dp(12) })

        val row = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }
        configureRoundButton(micButton, android.R.drawable.ic_btn_speak_now, "Gravar")
        configureRoundButton(pauseButton, android.R.drawable.ic_media_pause, "Pausar")
        val size = dp(64)
        row.addView(micButton, LayoutParams(size, size))
        row.addView(pauseButton, LayoutParams(size, size).apply { marginStart = dp(28) })
        addView(row, LayoutParams(MATCH, WRAP).apply { topMargin = dp(10) })

        micButton.setOnClickListener { startRecording() }
        pauseButton.setOnClickListener { stopRecording(STATUS_PAUSED) }
        refreshButtons()

        // Alguns operadores do Workspace (mapOverItems) fazem cast de getTag() para ItemInfo
        // sem checar null; esta etiqueta "não acionável" evita NPE. Nunca é gravada no banco.
        tag = ItemInfo().apply {
            itemType = LauncherSettings.Favorites.ITEM_TYPE_NON_ACTIONABLE
            container = LauncherSettings.Favorites.CONTAINER_DESKTOP
            screenId = XaulinXsMiscSettings.IDEA_SCREEN_ID
        }
        setOnLongClickListener { true }
    }

    // CellLayout.measureChild() aplica padding de ícone em qualquer filho; ignoramos.
    override fun setPadding(left: Int, top: Int, right: Int, bottom: Int) = Unit

    // ------------------------------------------------------------------
    // Construção da UI
    // ------------------------------------------------------------------

    private fun dp(value: Int): Int = (value * density).toInt()

    private fun configureInput() {
        input.apply {
            hint = PAGE_TITLE
            setHintTextColor(0x99FFFFFF.toInt())
            setTextColor(Color.WHITE)
            textSize = 18f
            gravity = Gravity.TOP or Gravity.START
            inputType = InputType.TYPE_CLASS_TEXT or
                InputType.TYPE_TEXT_FLAG_MULTI_LINE or
                InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
            imeOptions = EditorInfo.IME_FLAG_NO_EXTRACT_UI
            // Quebra determinística: o mesmo critério é usado em measureHeight().
            breakStrategy = Layout.BREAK_STRATEGY_SIMPLE
            hyphenationFrequency = Layout.HYPHENATION_FREQUENCY_NONE
            setHorizontallyScrolling(false)
            isVerticalScrollBarEnabled = false
            overScrollMode = OVER_SCROLL_NEVER
            setPadding(dp(16), dp(14), dp(16), dp(14))
            // Retângulo translúcido com borda branca — sem linhas internas visíveis.
            background = GradientDrawable().apply {
                shape = GradientDrawable.RECTANGLE
                cornerRadius = dp(14).toFloat()
                setColor(0x26000000)
                setStroke(dp(2), 0xCCFFFFFF.toInt())
            }
        }

        val saved = XaulinXsIdeaStore.load(context)
        programmatic = true
        input.setText(saved)
        input.setSelection(saved.length)
        programmatic = false
        lastGoodText = saved

        input.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}

            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}

            override fun afterTextChanged(s: Editable?) {
                onTextEdited(s?.toString().orEmpty())
            }
        })
    }

    private fun configureRoundButton(button: ImageButton, iconRes: Int, description: String) {
        button.apply {
            setImageResource(iconRes)
            setColorFilter(Color.WHITE)
            scaleType = ImageView.ScaleType.CENTER_INSIDE
            contentDescription = description
            setPadding(dp(14), dp(14), dp(14), dp(14))
        }
    }

    private fun applyButtonStyle(button: ImageButton, enabled: Boolean, strokeColor: Int) {
        button.isEnabled = enabled
        button.alpha = if (enabled) 1f else 0.4f
        button.background = GradientDrawable().apply {
            shape = GradientDrawable.OVAL
            setColor(0x26000000)
            setStroke(dp(2), strokeColor)
        }
    }

    private fun refreshButtons() {
        // Microfone fica vermelho enquanto grava.
        applyButtonStyle(
            micButton,
            enabled = !wantListening,
            strokeColor = if (wantListening) 0xFFFF5252.toInt() else 0xCCFFFFFF.toInt(),
        )
        applyButtonStyle(pauseButton, enabled = wantListening, strokeColor = 0xCCFFFFFF.toInt())
    }

    // ------------------------------------------------------------------
    // Ciclo de vida
    // ------------------------------------------------------------------

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        XaulinXsMiscPermissions.addListener(permissionListener)
        viewTreeObserver.addOnScrollChangedListener(scrollListener)
    }

    override fun onDetachedFromWindow() {
        super.onDetachedFromWindow()
        XaulinXsMiscPermissions.removeListener(permissionListener)
        if (viewTreeObserver.isAlive) viewTreeObserver.removeOnScrollChangedListener(scrollListener)
        wantListening = false
        acceptResults = false
        main.removeCallbacks(restartRunnable)
        main.removeCallbacks(stopAcceptRunnable)
        releaseRecognizer()
        XaulinXsIdeaStore.save(context, input.text?.toString().orEmpty())
    }

    override fun onWindowVisibilityChanged(visibility: Int) {
        super.onWindowVisibilityChanged(visibility)
        if (visibility != VISIBLE) {
            stopRecording(STATUS_IDLE)
            hideKeyboard()
        }
    }

    /** Rolou para outra página: para o microfone e fecha o teclado. */
    private fun onPageMoved() {
        if (!wantListening && !input.hasFocus()) return
        getLocationOnScreen(screenLoc)
        val screenWidth = resources.displayMetrics.widthPixels
        val visibleWidth = minOf(screenLoc[0] + width, screenWidth) - maxOf(screenLoc[0], 0)
        if (visibleWidth >= width / 2) return
        if (wantListening) stopRecording(STATUS_IDLE)
        if (input.hasFocus()) {
            input.clearFocus()
            hideKeyboard()
        }
    }

    private fun hideKeyboard() {
        val imm = context.getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager
        imm?.hideSoftInputFromWindow(windowToken, 0)
    }

    private fun toast(message: String) {
        Toast.makeText(context, message, Toast.LENGTH_SHORT).show()
    }

    // ------------------------------------------------------------------
    // Texto: limite de linhas pela altura real do retângulo
    // ------------------------------------------------------------------

    private fun measureHeight(text: CharSequence, widthPx: Int): Int =
        StaticLayout.Builder.obtain(text, 0, text.length, input.paint, widthPx)
            .setAlignment(Layout.Alignment.ALIGN_NORMAL)
            .setLineSpacing(input.lineSpacingExtra, input.lineSpacingMultiplier)
            .setIncludePad(input.includeFontPadding)
            .setBreakStrategy(Layout.BREAK_STRATEGY_SIMPLE)
            .setHyphenationFrequency(Layout.HYPHENATION_FREQUENCY_NONE)
            .build()
            .height

    /** true se [text] cabe inteiro no retângulo sem rolar. Sem layout ainda: não bloqueia. */
    private fun fits(text: CharSequence): Boolean {
        val availableWidth = input.width - input.paddingLeft - input.paddingRight
        val availableHeight = input.height - input.paddingTop - input.paddingBottom - dp(2)
        if (availableWidth <= 0 || availableHeight <= 0) return true
        return measureHeight(text, availableWidth) <= availableHeight
    }

    /** Maior prefixo de [candidate] que cabe, sem cortar abaixo de [minLength] nem no meio de palavra. */
    private fun fitPrefix(candidate: String, minLength: Int): String {
        if (fits(candidate)) return candidate
        var low = minLength.coerceIn(0, candidate.length)
        var high = candidate.length
        while (low < high) {
            val mid = (low + high + 1) / 2
            if (fits(candidate.substring(0, mid))) low = mid else high = mid - 1
        }
        var cut = low
        if (cut > 0 && Character.isHighSurrogate(candidate[cut - 1])) cut--
        // Corta na última fronteira de palavra do trecho novo, se houver.
        if (cut < candidate.length && !candidate[cut].isWhitespace()) {
            val boundary = candidate.substring(0, cut).lastIndexOfAny(charArrayOf(' ', '\n'))
            if (boundary >= minLength) cut = boundary
        }
        return candidate.substring(0, cut).trimEnd(' ')
    }

    private fun setTextProgrammatically(text: String, selection: Int = text.length) {
        programmatic = true
        try {
            input.setText(text)
            input.setSelection(selection.coerceIn(0, input.text.length))
        } finally {
            programmatic = false
        }
        lastGoodText = text
        XaulinXsIdeaStore.save(context, text)
    }

    /** Alteração vinda do usuário (teclado, colar, apagar). */
    private fun onTextEdited(current: String) {
        if (programmatic) return
        if (current.length > lastGoodText.length && !fits(current)) {
            // Passaria do que cabe na área visível: desfaz a entrada.
            val selection = minOf(input.selectionStart.coerceAtLeast(0), lastGoodText.length)
            setTextProgrammatically(lastGoodText, selection)
            statusView.text = STATUS_FULL
            return
        }
        lastGoodText = current
        XaulinXsIdeaStore.save(context, current)
        if (wantListening) {
            // Digitou durante a gravação: pausa para o ditado não sobrescrever o digitado.
            stopRecording(STATUS_PAUSED)
        }
        acceptResults = false
    }

    // ------------------------------------------------------------------
    // Ditado (SpeechRecognizer nativo)
    // ------------------------------------------------------------------

    private fun firstResult(bundle: Bundle?): String =
        bundle?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()

    private fun startRecording() {
        if (wantListening) return
        if (!XaulinXsMiscPermissions.hasMic(context)) {
            pendingStartAfterPermission = true
            XaulinXsMiscPermissionActivity.request(context, XaulinXsMiscPermissions.MIC)
            return
        }
        if (!SpeechRecognizer.isRecognitionAvailable(context)) {
            statusView.text = STATUS_UNAVAILABLE
            toast(STATUS_UNAVAILABLE)
            return
        }
        wantListening = true
        acceptResults = true
        consecutiveErrors = 0
        statusView.text = STATUS_LISTENING
        refreshButtons()
        beginSession()
    }

    private fun beginSession() {
        if (!wantListening) return
        val rec = recognizer ?: SpeechRecognizer.createSpeechRecognizer(context).also {
            it.setRecognitionListener(recognitionListener)
            recognizer = it
        }
        baseText = input.text?.toString().orEmpty()
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(
                RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM,
            )
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault().toLanguageTag())
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, context.packageName)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 3000L)
            putExtra(
                RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS,
                2500L,
            )
        }
        sessionActive = true
        try {
            rec.startListening(intent)
        } catch (e: Exception) {
            sessionActive = false
            stopRecording(STATUS_ERROR)
        }
    }

    private fun scheduleRestart(delayMs: Long) {
        main.removeCallbacks(restartRunnable)
        main.postDelayed(restartRunnable, delayMs)
    }

    private fun stopRecording(status: String) {
        val wasListening = wantListening
        wantListening = false
        pendingStartAfterPermission = false
        main.removeCallbacks(restartRunnable)
        if (wasListening && sessionActive) {
            // stopListening() ainda entrega o último trecho falado em onResults (aceito por ~1,5 s).
            try {
                recognizer?.stopListening()
            } catch (e: Exception) {
                releaseRecognizer()
            }
            main.removeCallbacks(stopAcceptRunnable)
            main.postDelayed(stopAcceptRunnable, 1500L)
        } else {
            acceptResults = false
        }
        refreshButtons()
        statusView.text = status
    }

    private fun releaseRecognizer() {
        sessionActive = false
        try {
            recognizer?.destroy()
        } catch (_: Exception) {
        }
        recognizer = null
    }

    private fun handleError(error: Int) {
        if (!wantListening) {
            acceptResults = false
            return
        }
        when (error) {
            // Silêncio / nada reconhecido: continua ouvindo.
            SpeechRecognizer.ERROR_NO_MATCH,
            SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> scheduleRestart(250)

            SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> stopRecording(STATUS_DENIED)

            SpeechRecognizer.ERROR_NETWORK,
            SpeechRecognizer.ERROR_NETWORK_TIMEOUT,
            SpeechRecognizer.ERROR_SERVER -> stopRecording(STATUS_NETWORK)

            else -> {
                consecutiveErrors++
                if (consecutiveErrors > MAX_CONSECUTIVE_ERRORS) {
                    stopRecording(STATUS_ERROR)
                } else {
                    // BUSY / CLIENT / AUDIO: recria o reconhecedor e tenta de novo.
                    releaseRecognizer()
                    scheduleRestart(600)
                }
            }
        }
    }

    /** Anexa a fala ao texto que já existia no início da sessão (nunca apaga o que estava lá). */
    private fun applySpeech(spoken: String) {
        val piece = spoken.trim()
        if (piece.isEmpty()) return
        val separator = if (baseText.isEmpty() || baseText.last().isWhitespace()) "" else " "
        val candidate = baseText + separator + piece
        val fitted = fitPrefix(candidate, baseText.length)
        setTextProgrammatically(fitted)
        if (fitted.length < candidate.length) {
            // Acabou o espaço visível: para de gravar e avisa.
            stopRecording(STATUS_FULL)
            acceptResults = false
        }
    }

    private fun onPermissionResult() {
        if (!pendingStartAfterPermission) return
        pendingStartAfterPermission = false
        if (XaulinXsMiscPermissions.hasMic(context)) {
            startRecording()
        } else {
            statusView.text = STATUS_DENIED
            toast(STATUS_DENIED)
        }
    }
}
'''

FILE_MISC_SETTINGS = ROOT / f"{CUST}/misc/XaulinXsMiscSettings.kt"

OLD_MS_ID = "    const val MUSIC_SCREEN_ID = -300\n"
NEW_MS_ID = '''    const val MUSIC_SCREEN_ID = -300

    /**
     * Id de "screen" reservado da página "Sua Ideia..." (sempre a ÚLTIMA página). Negativo pelo
     * mesmo motivo do da música (nunca removida como "página vazia") e distinto de -200, -201
     * (páginas extras vazias) e -300 (música).
     */
    const val IDEA_SCREEN_ID = -301
'''

OLD_MS_ENABLED = '''    @JvmField
    val WEATHER_ENABLED = backedUpItem("xaulinxs_weather_enabled", true)
'''
NEW_MS_ENABLED = OLD_MS_ENABLED + '''
    // Página "Sua Ideia...": ligada por padrão; desativa em R's Misc (reinicia o launcher).
    @JvmField
    val IDEA_PAGE_ENABLED = backedUpItem("xaulinxs_idea_page_enabled", true)
'''

OLD_MS_FUN = '''    @JvmStatic
    fun isWeatherEnabled(context: Context): Boolean =
        LauncherPrefs.get(context).get(WEATHER_ENABLED)
}
'''
NEW_MS_FUN = '''    @JvmStatic
    fun isWeatherEnabled(context: Context): Boolean =
        LauncherPrefs.get(context).get(WEATHER_ENABLED)

    @JvmStatic
    fun isIdeaPageEnabled(context: Context): Boolean =
        LauncherPrefs.get(context).get(IDEA_PAGE_ENABLED)
}
'''

FILE_MISC_PERM = ROOT / f"{CUST}/misc/XaulinXsMiscPermissionActivity.kt"

OLD_PERM_MIC = '''    private val listeners = java.util.concurrent.CopyOnWriteArrayList<Runnable>()
    private val main = Handler(Looper.getMainLooper())
'''
NEW_PERM_MIC = '''    // Página "Sua Ideia...": ditado por voz (SpeechRecognizer).
    @JvmStatic
    val MIC = arrayOf(android.Manifest.permission.RECORD_AUDIO)

''' + OLD_PERM_MIC

OLD_PERM_HAS = '''    @JvmStatic
    fun hasAudio(c: Context) = AUDIO.all {
        ContextCompat.checkSelfPermission(c, it) == PackageManager.PERMISSION_GRANTED
    }
}
'''
NEW_PERM_HAS = '''    @JvmStatic
    fun hasAudio(c: Context) = AUDIO.all {
        ContextCompat.checkSelfPermission(c, it) == PackageManager.PERMISSION_GRANTED
    }

    @JvmStatic
    fun hasMic(c: Context) = MIC.all {
        ContextCompat.checkSelfPermission(c, it) == PackageManager.PERMISSION_GRANTED
    }
}
'''

FILE_MISC_TOGGLES = ROOT / f"{CUST}/settings/MiscToggles.kt"

OLD_TOGGLE_END = '''            // O Launcher relê o interruptor no onResume ao voltar para a tela inicial.
            true
        }
    }
}
'''
NEW_TOGGLE_END = OLD_TOGGLE_END + '''
/** Liga/desliga a página "Sua Ideia...". A página nasce no bind do Workspace, então reinicia o app. */
class IdeaPageEnabledPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = XaulinXsMiscSettings.isIdeaPageEnabled(context)
        setOnPreferenceChangeListener { _, newValue ->
            val enabled = newValue as Boolean
            LauncherPrefs.get(context).put(XaulinXsMiscSettings.IDEA_PAGE_ENABLED, enabled)
            (context as? Activity)?.let { XaulinXsAppRestarter.restart(it) }
            true
        }
    }
}
'''

OLD_PREFS_MISC = '''            <com.xaulinxs.customizations.settings.WeatherEnabledPreference
                android:key="xaulinxs_weather_enabled"
                android:title="@string/xaulinxs_weather_title"
                android:summary="@string/xaulinxs_weather_summary"
                android:persistent="false" />
'''
NEW_PREFS_MISC = OLD_PREFS_MISC + '''
            <com.xaulinxs.customizations.settings.IdeaPageEnabledPreference
                android:key="xaulinxs_idea_page_enabled"
                android:title="@string/xaulinxs_idea_page_title"
                android:summary="@string/xaulinxs_idea_page_summary"
                android:persistent="false" />
'''

OLD_STR_MISC = '    <string name="xaulinxs_cat_misc_summary">Player de música e widget de clima</string>\n'
NEW_STR_MISC = '''    <string name="xaulinxs_cat_misc_summary">Player de música, widget de clima e página Sua Ideia...</string>
    <string name="xaulinxs_idea_page_title">Página Sua Ideia...</string>
    <string name="xaulinxs_idea_page_summary">Última página fixa da tela inicial: ditado por voz (reconhecimento nativo do Android) e campo de texto que nunca é apagado (reinicia o launcher)</string>
'''

FILE_IDS = ROOT / "res/values/xaulinxs_ids.xml"
OLD_IDS = '    <item name="xaulinxs_music_page" type="id" />\n'
NEW_IDS = OLD_IDS + '    <item name="xaulinxs_idea_page" type="id" />\n'

FILE_MANIFEST = ROOT / "AndroidManifest.xml"
OLD_MANIFEST = '    <uses-permission android:name="android.permission.READ_MEDIA_AUDIO" />\n'
NEW_MANIFEST = OLD_MANIFEST + '''    <!-- XaulinXs R's Misc: página "Sua Ideia..." (ditado por voz) -->
    <uses-permission android:name="android.permission.RECORD_AUDIO" />
'''

FILE_WORKSPACE = ROOT / "src/com/android/launcher3/Workspace.java"

OLD_WS_CALL = '''        xaulinXsInsertMusicPageIfEnabled();
    }
'''
NEW_WS_CALL = '''        xaulinXsInsertMusicPageIfEnabled();
        // XaulinXs R's Misc: página "Sua Ideia..." como ÚLTIMA página (sempre depois das demais).
        xaulinXsInsertIdeaPageIfEnabled();
    }
'''

OLD_WS_ANCHOR = '''    /**
     * XaulinXs R's Misc: 1 quando a primeira página está centralizada, 0 quando já
'''
NEW_WS_METHODS = '''    /**
     * XaulinXs R's Misc — não faz parte do AOSP original.
     * Cria a página fixa "Sua Ideia..." (ditado por voz + campo de texto) como ÚLTIMA página.
     * Mesmo esquema da página de música: id negativo (nunca removida como "página vazia") e
     * grade inteira ocupada pelo conteúdo (nenhum item pode ser solto nela). Ela nasce aqui, no
     * início do bind, e é mantida por último por insertNewWorkspaceScreen() e
     * xaulinXsAddToScreenOrder(): toda página criada depois (páginas do usuário vindas do banco,
     * página vazia extra do arrasto) entra ANTES dela.
     */
    private void xaulinXsInsertIdeaPageIfEnabled() {
        if (!com.xaulinxs.customizations.misc.XaulinXsMiscSettings
                .isIdeaPageEnabled(getContext())) {
            return;
        }
        final int id = com.xaulinxs.customizations.misc.XaulinXsMiscSettings.IDEA_SCREEN_ID;
        if (mWorkspaceScreens.containsKey(id)) return;
        CellLayout page = insertNewWorkspaceScreen(id, getChildCount());
        com.xaulinxs.customizations.misc.idea.XaulinXsIdeaPageView content =
                new com.xaulinxs.customizations.misc.idea.XaulinXsIdeaPageView(getContext());
        CellLayoutLayoutParams lp = new CellLayoutLayoutParams(
                0, 0, page.getCountX(), page.getCountY());
        lp.canReorder = false;
        page.addViewToCellLayout(content, -1, R.id.xaulinxs_idea_page, lp, true);
    }

    /**
     * XaulinXs R's Misc: limita o índice de inserção para que nada fique DEPOIS da página
     * "Sua Ideia..." (quando ela existe).
     */
    private int xaulinXsClampBeforeIdeaPage(int screenId, int insertIndex) {
        final int ideaId = com.xaulinxs.customizations.misc.XaulinXsMiscSettings.IDEA_SCREEN_ID;
        if (screenId == ideaId) return insertIndex;
        final int ideaIndex = mScreenOrder.indexOf(ideaId);
        return (ideaIndex >= 0 && insertIndex > ideaIndex) ? ideaIndex : insertIndex;
    }

    /** XaulinXs R's Misc: mScreenOrder.add(screenId) que respeita "Sua Ideia..." como última. */
    private void xaulinXsAddToScreenOrder(int screenId) {
        mScreenOrder.add(xaulinXsClampBeforeIdeaPage(screenId, mScreenOrder.size()), screenId);
    }

'''
NEW_WS_ANCHOR = NEW_WS_METHODS + OLD_WS_ANCHOR

OLD_WS_INSERT = '''        if (mWorkspaceScreens.containsKey(screenId)) {
            throw new RuntimeException("Screen id " + screenId + " already exists!");
        }
'''
NEW_WS_INSERT = OLD_WS_INSERT + '''        // XaulinXs R's Misc: "Sua Ideia..." é sempre a última página — novas páginas entram antes.
        insertIndex = xaulinXsClampBeforeIdeaPage(screenId, insertIndex);
'''

OLD_WS_ORDER_1 = '''            mWorkspaceScreens.put(newScreenId, screen);
            mScreenOrder.add(newScreenId);
'''
NEW_WS_ORDER_1 = '''            mWorkspaceScreens.put(newScreenId, screen);
            xaulinXsAddToScreenOrder(newScreenId);
'''

OLD_WS_ORDER_2 = '''        mWorkspaceScreens.put(newScreenId, cl);
        mScreenOrder.add(newScreenId);
'''
NEW_WS_ORDER_2 = '''        mWorkspaceScreens.put(newScreenId, cl);
        xaulinXsAddToScreenOrder(newScreenId);
'''

OLD_WS_ORDER_3 = '''                mWorkspaceScreens.put(extraScreenId, cl);
                mScreenOrder.add(extraScreenId);
'''
NEW_WS_ORDER_3 = '''                mWorkspaceScreens.put(extraScreenId, cl);
                xaulinXsAddToScreenOrder(extraScreenId);
'''


def main() -> int:
    if not Path("gradlew").exists():
        print("ERRO: rode este script na raiz do checkout (onde está o gradlew).")
        return 1

    print("== 1) Véu temático separado do desfoque ==")
    write_new_file(FILE_VEIL_PREF, CONTENT_VEIL_PREF)
    apply_patch(FILE_GRADIENT_VIEW, OLD_GV_IMPORT, NEW_GV_IMPORT, "WallpaperGradientView: imports")
    apply_patch(FILE_GRADIENT_VIEW, OLD_GV_FIELD, NEW_GV_FIELD, "WallpaperGradientView: listener")
    apply_patch(FILE_GRADIENT_VIEW, OLD_GV_ATTACH, NEW_GV_ATTACH, "WallpaperGradientView: attach")
    apply_patch(FILE_GRADIENT_VIEW, OLD_GV_DETACH, NEW_GV_DETACH, "WallpaperGradientView: detach")
    apply_patch(FILE_GRADIENT_VIEW, OLD_GV_GATE, NEW_GV_GATE, "WallpaperGradientView: gate do véu")
    apply_patch(FILE_PREFS_XML, OLD_PREFS_SCRIM, NEW_PREFS_SCRIM, "preferences: interruptor do véu")
    apply_patch(FILE_STRINGS, OLD_STR_SCRIM, NEW_STR_SCRIM, "strings: véu")

    print("== 2) Design da QSB (QuickSearchBox transparente) ==")
    write_new_file(FILE_QSB_BG, CONTENT_QSB_BG)
    write_new_file(FILE_QSB_MIC, CONTENT_QSB_MIC)
    apply_patch(FILE_QSB_LAYOUT, OLD_QSB_PAD, NEW_QSB_PAD, "QSB layout: paddings/ícone")
    apply_patch(FILE_QSB_LAYOUT, OLD_QSB_BG, NEW_QSB_BG, "QSB layout: fundo/cor do texto")
    apply_patch(FILE_OSE_VIEW, OLD_OSE_LISTENER, NEW_OSE_LISTENER, "OseWidgetView: listener de cor")
    apply_patch(FILE_OSE_VIEW, OLD_OSE_TINT, NEW_OSE_TINT, "OseWidgetView: cor do ícone")
    apply_patch(FILE_OSE_VIEW, OLD_OSE_REFRESH, NEW_OSE_REFRESH, "OseWidgetView: refresh do ícone")
    apply_patch(FILE_OSE_VIEW, OLD_OSE_APPEARANCE, NEW_OSE_APPEARANCE, "OseWidgetView: cor de bordas/texto")
    apply_patch(FILE_QSB_CONFIG, OLD_QSB_DEFAULT, NEW_QSB_DEFAULT, "QsbConfig: cor padrão branca")
    apply_patch(FILE_STRINGS, OLD_STR_QSB_COLOR, NEW_STR_QSB_COLOR, "strings: rótulo Cor da barra")

    print("== 3) Desfoque da tela inicial com wallpaper do sistema ==")
    apply_patch(FILE_WALLPAPER_VIEW, OLD_WV_PREFCHANGED, NEW_WV_PREFCHANGED, "WallpaperView: listener do slider")
    apply_patch(FILE_WALLPAPER_VIEW, OLD_WV_APPLY, NEW_WV_APPLY, "WallpaperView: raio do blur")
    apply_patch(FILE_WALLPAPER_VIEW, OLD_WV_PRELOAD, NEW_WV_PRELOAD, "WallpaperView: pré-carga da cópia")
    apply_patch(FILE_WALLPAPER_VIEW, OLD_WV_RADIUS, NEW_WV_RADIUS, "WallpaperView: raio da cópia")
    apply_patch(FILE_WALLPAPER_VIEW, OLD_WV_ALPHA, NEW_WV_ALPHA, "WallpaperView: alpha da cópia")

    print("== 4) Página Sua Ideia... ==")
    write_new_file(FILE_IDEA_VIEW, CONTENT_IDEA_VIEW)
    apply_patch(FILE_MISC_SETTINGS, OLD_MS_ID, NEW_MS_ID, "MiscSettings: IDEA_SCREEN_ID")
    apply_patch(FILE_MISC_SETTINGS, OLD_MS_ENABLED, NEW_MS_ENABLED, "MiscSettings: IDEA_PAGE_ENABLED")
    apply_patch(FILE_MISC_SETTINGS, OLD_MS_FUN, NEW_MS_FUN, "MiscSettings: isIdeaPageEnabled")
    apply_patch(FILE_MISC_PERM, OLD_PERM_MIC, NEW_PERM_MIC, "Permissões: MIC")
    apply_patch(FILE_MISC_PERM, OLD_PERM_HAS, NEW_PERM_HAS, "Permissões: hasMic")
    apply_patch(FILE_MISC_TOGGLES, OLD_TOGGLE_END, NEW_TOGGLE_END, "MiscToggles: IdeaPageEnabledPreference")
    apply_patch(FILE_PREFS_XML, OLD_PREFS_MISC, NEW_PREFS_MISC, "preferences: R's Misc")
    apply_patch(FILE_STRINGS, OLD_STR_MISC, NEW_STR_MISC, "strings: R's Misc / Sua Ideia")
    apply_patch(FILE_IDS, OLD_IDS, NEW_IDS, "ids: xaulinxs_idea_page")
    apply_patch(FILE_MANIFEST, OLD_MANIFEST, NEW_MANIFEST, "Manifest: RECORD_AUDIO")
    apply_patch(FILE_WORKSPACE, OLD_WS_CALL, NEW_WS_CALL, "Workspace: chamada no bind")
    apply_patch(FILE_WORKSPACE, OLD_WS_ANCHOR, NEW_WS_ANCHOR, "Workspace: métodos da página")
    apply_patch(FILE_WORKSPACE, OLD_WS_INSERT, NEW_WS_INSERT, "Workspace: insert antes da Ideia")
    apply_patch(FILE_WORKSPACE, OLD_WS_ORDER_1, NEW_WS_ORDER_1, "Workspace: ordem (convert final)")
    apply_patch(FILE_WORKSPACE, OLD_WS_ORDER_2, NEW_WS_ORDER_2, "Workspace: ordem (commit extra)")
    apply_patch(FILE_WORKSPACE, OLD_WS_ORDER_3, NEW_WS_ORDER_3, "Workspace: ordem (strip)")

    print()
    if errors:
        print("=== CONCLUÍDO COM AVISOS ===")
        for e in errors:
            print(e)
        return 1

    print("=== TUDO APLICADO COM SUCESSO ===")
    print("  1) Véu temático: interruptor próprio em Menu de aplicativo (padrão desligado)")
    print("  2) QSB: placa/campo/botão de voz estilo QuickSearchBox, transparente, bordas brancas")
    print("  3) Desfoque da tela inicial agora vale também com o wallpaper do app desligado")
    print("  4) Página 'Sua Ideia...' como última página + interruptor em R's Misc")
    print()
    print("Agora rode: ./gradlew assembleNoQuickstepDebug")
    return 0


if __name__ == "__main__":
    sys.exit(main())
