#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XaulinXsLauncher3 — desfoque do papel de parede + "Ícones desfocados".

Rode na RAIZ do repositório:

    python3 apply_wallpaper_blur_and_icon_blur.py            # aplica
    python3 apply_wallpaper_blur_and_icon_blur.py --dry-run  # só mostra o que faria

O que muda:

1) "Fundo desfocado no menu de apps" (THEMED_SCRIM_ENABLED) deixa de borrar a
   workspace/hotseat inteiras. Agora ele borra o PAPEL DE PAREDE
   (XaulinXsWallpaperView), com o mesmo raio e a mesma curva (progresso do
   arrasto de abrir/fechar o app drawer) que antes eram aplicados na workspace.

2) Nova customization "Ícones desfocados" (categoria Ícone): interruptor +
   slider de intensidade 0-200%. Aplica o MESMO desfoque do arrasto do drawer,
   mas só nos ícones (BubbleTextView e FolderIcon) da workspace e do hotseat —
   widgets ficam de fora.

O desfoque do balão de contexto (long-press) continua como estava.

O script é idempotente (marcador XAULINXS_ICON_BLUR_V1) e só grava se TODOS
os trechos-âncora forem encontrados — nada é escrito pela metade.
"""
import sys
from pathlib import Path

MARK = "XAULINXS_ICON_BLUR_V1"
DRY = "--dry-run" in sys.argv

ROOT = Path.cwd()
CUST = ROOT / "modules/customizations/src/com/xaulinxs/customizations"

F_DEPTH = CUST / "blur/XaulinXsDepthController.kt"
F_WALLVIEW = CUST / "theme/XaulinXsWallpaperView.kt"
F_ICONBLUR = CUST / "icons/XaulinXsIconBlur.kt"
F_PREF_EN = CUST / "settings/IconBlurEnabledPreference.kt"
F_PREF_PCT = CUST / "settings/IconBlurPercentPreference.kt"
F_PREFS_XML = ROOT / "res/xml/launcher_preferences.xml"
F_STRINGS = ROOT / "res/values/xaulinxs_strings.xml"


def die(msg):
    print("ERRO: " + msg)
    sys.exit(1)


# --------------------------------------------------------------------------
# Conteúdo dos arquivos novos / reescritos
# --------------------------------------------------------------------------

ICON_BLUR_KT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 * XAULINXS_ICON_BLUR_V1
 *
 * "Ícones desfocados": replica nos ícones o mesmo desfoque que a workspace
 * recebia durante o arrasto de abertura/fechamento do app drawer, mas SÓ nos
 * ícones (BubbleTextView e FolderIcon da workspace e do hotseat). Widgets e
 * a barra de busca não são tocados.
 *
 * O raio é (progresso do arrasto 0..1) * BASE_MAX_RADIUS_PX * (percentual/100).
 * BASE_MAX_RADIUS_PX é o mesmo raio máximo que o drawer sempre usou (320px),
 * então 100% reproduz exatamente o desfoque de antes; 200% dobra.
 */
package com.xaulinxs.customizations.icons

import android.content.Context
import android.graphics.RenderEffect
import android.graphics.Shader
import android.os.Build
import android.view.View
import com.android.launcher3.BubbleTextView
import com.android.launcher3.CellLayout
import com.android.launcher3.Launcher
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem
import com.android.launcher3.folder.FolderIcon

object XaulinXsIconBlur {
    private const val KEY_ICON_BLUR_ENABLED = "xaulinxs_icon_blur_enabled"
    private const val KEY_ICON_BLUR_PERCENT = "xaulinxs_icon_blur_percent"

    const val MIN_PERCENT = 0
    const val MAX_PERCENT = 200
    const val DEFAULT_PERCENT = 100

    // Mesmo raio máximo do desfoque do app drawer (antes aplicado na workspace inteira).
    const val BASE_MAX_RADIUS_PX = 320f

    // Ligado por padrão para preservar o visual de antes (ícones borrando no arrasto).
    @JvmField
    val ICON_BLUR_ENABLED = backedUpItem(KEY_ICON_BLUR_ENABLED, true)

    @JvmField
    val ICON_BLUR_PERCENT = backedUpItem(KEY_ICON_BLUR_PERCENT, DEFAULT_PERCENT)

    /** Raio máximo (progresso = 1) em px; 0 quando desligado ou em 0%. */
    @JvmStatic
    fun getMaxRadiusPx(context: Context): Float {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return 0f
        val prefs = LauncherPrefs.get(context)
        if (!prefs.get(ICON_BLUR_ENABLED)) return 0f
        val percent = prefs.get(ICON_BLUR_PERCENT).coerceIn(MIN_PERCENT, MAX_PERCENT)
        return BASE_MAX_RADIUS_PX * percent / 100f
    }

    /** Aplica (ou remove, se radiusPx < 1) o desfoque em todos os ícones da home e do hotseat. */
    @JvmStatic
    fun applyRadius(launcher: Launcher, radiusPx: Float) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return
        // Um único RenderEffect compartilhado por todos os ícones (um por frame, não um por ícone).
        val effect = if (radiusPx >= 1f) {
            RenderEffect.createBlurEffect(radiusPx, radiusPx, Shader.TileMode.CLAMP)
        } else {
            null
        }
        val workspace = launcher.workspace
        if (workspace != null) {
            for (i in 0 until workspace.childCount) {
                val page = workspace.getChildAt(i)
                if (page is CellLayout) applyToLayout(page, effect)
            }
        }
        val hotseat = launcher.hotseat
        if (hotseat != null) applyToLayout(hotseat, effect)
    }

    private fun applyToLayout(layout: CellLayout, effect: RenderEffect?) {
        val container = layout.shortcutsAndWidgets
        for (j in 0 until container.childCount) {
            val child: View = container.getChildAt(j)
            if (child is BubbleTextView || child is FolderIcon) {
                child.setRenderEffect(effect)
            }
        }
    }
}
'''

PREF_ENABLED_KT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 * XAULINXS_ICON_BLUR_V1
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.icons.XaulinXsIconBlur

class IconBlurEnabledPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(XaulinXsIconBlur.ICON_BLUR_ENABLED)
        setOnPreferenceChangeListener { _, newValue ->
            // Não precisa forçar nada: o raio é relido a cada frame do próximo arrasto do drawer.
            LauncherPrefs.get(context).put(XaulinXsIconBlur.ICON_BLUR_ENABLED, newValue as Boolean)
            true
        }
    }
}
'''

PREF_PERCENT_KT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 * XAULINXS_ICON_BLUR_V1
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.icons.XaulinXsIconBlur

class IconBlurPercentPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = XaulinXsIconBlur.MIN_PERCENT
        max = XaulinXsIconBlur.MAX_PERCENT
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(XaulinXsIconBlur.ICON_BLUR_PERCENT)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(XaulinXsIconBlur.ICON_BLUR_PERCENT, newValue as Int)
            true
        }
    }
}
'''

DEPTH_CONTROLLER_KT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 * XAULINXS_ICON_BLUR_V1
 *
 * Desfoque sincronizado com o arrasto de abrir/fechar o App Drawer, sem
 * depender do flavor Quickstep (o DepthController do AOSP exige o
 * SystemUiProxy). Usa RenderEffect — a mesma técnica de
 * com.android.launcher3.organizer.creation.screen.ui.BlurController.
 *
 * Três destinos independentes, todos com o mesmo raio-base (320px * progresso):
 *
 *  1) PAPEL DE PAREDE (XaulinXsWallpaperView) — controlado por
 *     "Fundo desfocado no menu de apps" (THEMED_SCRIM_ENABLED).
 *  2) ÍCONES da home/hotseat — controlado por "Ícones desfocados"
 *     (XaulinXsIconBlur: interruptor + slider 0-200%).
 *  3) BALÃO DE CONTEXTO (long-press) — comportamento antigo, intacto: blur de
 *     janela + RenderEffect na workspace/hotseat com raio fixo.
 *
 * Quando o wallpaper próprio do launcher está desligado (o wallpaper real do
 * sistema aparece por trás), não há view nossa para borrar; nesse caso o
 * desfoque do drawer cai para o blur de janela (FLAG_BLUR_BEHIND), como antes.
 */
package com.xaulinxs.customizations.blur

import android.graphics.RenderEffect
import android.graphics.Shader
import android.os.Build
import android.util.Log
import android.view.View
import android.view.WindowManager
import android.view.WindowManager.LayoutParams.FLAG_BLUR_BEHIND
import android.view.WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS
import com.android.launcher3.Launcher
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.R
import com.xaulinxs.customizations.icons.XaulinXsIconBlur
import com.xaulinxs.customizations.settings.ThemedScrimPreference.Companion.THEMED_SCRIM_ENABLED
import com.xaulinxs.customizations.theme.XaulinXsInAppWallpaperSetting
import com.xaulinxs.customizations.theme.XaulinXsWallpaperView

// Raio máximo do desfoque do drawer (progresso = 1). 320px (~128dp em xxhdpi).
// É o mesmo valor que antes era aplicado na workspace inteira.
private const val DRAWER_MAX_BLUR_RADIUS_PX = 320f

// Raio atrás de um balão de contexto (long-press), aplicado de forma
// instantânea — um raio muito alto de uma vez gera artefato visual.
private const val POPUP_BLUR_RADIUS_PX = 70f

private const val TAG = "XaulinXsDepthController"

class XaulinXsDepthController(private val launcher: Launcher) {

    private var currentDepth = 0f
    private var popupBlurActive = false

    // Últimos valores aplicados (px, inteiros) — evita trabalho repetido a cada frame.
    private var appliedWallpaperRadius = -1
    private var appliedIconRadius = -1
    private var appliedWindowRadius = -1
    private var appliedPopupRadius = -1

    private var wallpaperView: XaulinXsWallpaperView? = null

    private val isEnabled: Boolean
        get() = LauncherPrefs.get(launcher).get(THEMED_SCRIM_ENABLED)

    private val isInAppWallpaperEnabled: Boolean
        get() = LauncherPrefs.get(launcher).get(XaulinXsInAppWallpaperSetting.IN_APP_WALLPAPER_ENABLED)

    fun setupWindowBlurFlags() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            launcher.window?.addFlags(FLAG_BLUR_BEHIND)
            launcher.window?.addFlags(FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)

            val windowManager = launcher.getSystemService(WindowManager::class.java)
            windowManager?.addCrossWindowBlurEnabledListener { enabled ->
                Log.d(TAG, "Cross-window blur enabled pelo sistema: $enabled")
            }
        }
        XaulinXsWindowBlurStateHolder.setBlurEnabled(
            isEnabled && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S
        )
    }

    /** Chamado a cada frame do arrasto (0 = home, 1 = drawer aberto). */
    fun setDepth(depth: Float) {
        currentDepth = depth.coerceIn(0f, 1f)
        XaulinXsWindowBlurStateHolder.setBlurEnabled(
            isEnabled && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S
        )
        applyWallpaperBlur()
        applyIconBlur()
        applyWindowAndPopupBlur()
    }

    fun setPopupBlurActive(active: Boolean) {
        if (popupBlurActive == active) return
        popupBlurActive = active
        applyWindowAndPopupBlur()
    }

    // ---- 1) papel de parede --------------------------------------------------

    private fun applyWallpaperBlur() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return
        val radius = if (isEnabled) (currentDepth * DRAWER_MAX_BLUR_RADIUS_PX).toInt() else 0
        if (radius == appliedWallpaperRadius) return
        appliedWallpaperRadius = radius
        findWallpaperView()?.setDepthBlurRadiusPx(radius.toFloat())
    }

    private fun findWallpaperView(): XaulinXsWallpaperView? {
        if (wallpaperView == null) {
            val v: View? = launcher.findViewById(R.id.xaulinxs_wallpaper_view)
            wallpaperView = v as? XaulinXsWallpaperView
        }
        return wallpaperView
    }

    // ---- 2) ícones -----------------------------------------------------------

    private fun applyIconBlur() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return
        val radius = (currentDepth * XaulinXsIconBlur.getMaxRadiusPx(launcher)).toInt()
        if (radius == appliedIconRadius) return
        appliedIconRadius = radius
        XaulinXsIconBlur.applyRadius(launcher, radius.toFloat())
    }

    // ---- 3) balão de contexto + fallback de janela ---------------------------

    private fun applyWindowAndPopupBlur() {
        val drawerWindowRadius =
            if (isEnabled && !isInAppWallpaperEnabled) currentDepth * DRAWER_MAX_BLUR_RADIUS_PX else 0f
        val popupRadius = if (popupBlurActive) POPUP_BLUR_RADIUS_PX else 0f
        val windowRadius = maxOf(drawerWindowRadius, popupRadius).toInt()
        val popupInt = popupRadius.toInt()
        if (windowRadius == appliedWindowRadius && popupInt == appliedPopupRadius) return
        appliedWindowRadius = windowRadius
        appliedPopupRadius = popupInt
        applyWindowAndPopup(windowRadius, popupInt)
    }

    private fun applyWindowAndPopup(windowRadius: Int, popupRadius: Int) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return

        val window = launcher.window
        if (window != null) {
            try {
                window.attributes = window.attributes.apply { blurBehindRadius = windowRadius }
            } catch (_: Exception) {
            }
        }

        val effect = if (popupRadius > 1) {
            RenderEffect.createBlurEffect(
                popupRadius.toFloat(), popupRadius.toFloat(), Shader.TileMode.CLAMP
            )
        } else {
            null
        }
        for (view in launcher.depthBlurTargets) {
            view.setRenderEffect(effect)
        }
    }
}
'''

STRINGS_NEW = '''    <string name="xaulinxs_icon_blur_enabled_title">Ícones desfocados</string>
    <string name="xaulinxs_icon_blur_enabled_summary">Desfoca os ícones da tela inicial ao abrir/fechar o menu de apps, com o mesmo efeito do arrasto (só os ícones, widgets não)</string>
    <string name="xaulinxs_icon_blur_percent_title">Intensidade do desfoque dos ícones</string>
    <string name="xaulinxs_icon_blur_percent_summary">0% a 200% (100% = intensidade original do arrasto do menu de apps)</string>
'''

PREFS_XML_NEW = '''            <com.xaulinxs.customizations.settings.IconBlurEnabledPreference
                android:key="xaulinxs_icon_blur_enabled"
                android:title="@string/xaulinxs_icon_blur_enabled_title"
                android:summary="@string/xaulinxs_icon_blur_enabled_summary"
                android:persistent="false" />

            <com.xaulinxs.customizations.settings.IconBlurPercentPreference
                android:key="xaulinxs_icon_blur_percent"
                android:title="@string/xaulinxs_icon_blur_percent_title"
                android:summary="@string/xaulinxs_icon_blur_percent_summary"
                android:dependency="xaulinxs_icon_blur_enabled"
                android:persistent="false" />

'''


# --------------------------------------------------------------------------
# Pré-checagens
# --------------------------------------------------------------------------

for p in (F_DEPTH, F_WALLVIEW, F_PREFS_XML, F_STRINGS):
    if not p.exists():
        die("não achei %s — rode o script na RAIZ do repositório." % p)

writes = {}  # Path -> novo conteúdo (só grava no fim, se tudo deu certo)
notes = []


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        die("âncora '%s' encontrada %d vez(es) (esperado 1). O arquivo mudou? Nada foi alterado." % (label, n))
    return text.replace(old, new)


# 1) XaulinXsDepthController.kt — reescrita completa
depth_src = F_DEPTH.read_text(encoding="utf-8")
if MARK in depth_src:
    notes.append("já aplicado: XaulinXsDepthController.kt")
elif "DRAWER_MAX_BLUR_RADIUS_PX" not in depth_src or "setPopupBlurActive" not in depth_src:
    die("XaulinXsDepthController.kt não tem o formato esperado; abortando sem alterar nada.")
else:
    writes[F_DEPTH] = DEPTH_CONTROLLER_KT

# 2) XaulinXsWallpaperView.kt — raio de profundidade somado ao desfoque estático
wall_src = F_WALLVIEW.read_text(encoding="utf-8")
if "setDepthBlurRadiusPx" in wall_src:
    notes.append("já aplicado: XaulinXsWallpaperView.kt")
else:
    wall_src = replace_once(
        wall_src,
        "    private val onEnabledPrefChanged: () -> Unit = { post { applyBlurEffect(); invalidate() } }\n",
        "    private val onEnabledPrefChanged: () -> Unit = { post { applyBlurEffect(); invalidate() } }\n"
        "\n"
        "    // " + MARK + ": raio vindo do arrasto do app drawer (XaulinXsDepthController).\n"
        "    // O raio final é o MAIOR entre o desfoque fixo da tela inicial e este.\n"
        "    private var depthBlurRadiusPx = 0f\n",
        "onEnabledPrefChanged",
    )
    wall_src = replace_once(
        wall_src,
        "        val radiusPx = XaulinXsWorkspaceBlur.getBlurRadiusPx(context)\n",
        "        val radiusPx = maxOf(XaulinXsWorkspaceBlur.getBlurRadiusPx(context), depthBlurRadiusPx)\n",
        "getBlurRadiusPx",
    )
    wall_src = replace_once(
        wall_src,
        "    private fun isInAppWallpaperEnabled(): Boolean =\n",
        "    /** Chamado pelo XaulinXsDepthController a cada frame do arrasto do app drawer. */\n"
        "    fun setDepthBlurRadiusPx(radiusPx: Float) {\n"
        "        if (radiusPx == depthBlurRadiusPx) return\n"
        "        depthBlurRadiusPx = radiusPx\n"
        "        applyBlurEffect()\n"
        "    }\n"
        "\n"
        "    private fun isInAppWallpaperEnabled(): Boolean =\n",
        "isInAppWallpaperEnabled",
    )
    writes[F_WALLVIEW] = wall_src

# 3) Arquivos novos
for path, content in ((F_ICONBLUR, ICON_BLUR_KT), (F_PREF_EN, PREF_ENABLED_KT), (F_PREF_PCT, PREF_PERCENT_KT)):
    if path.exists() and MARK in path.read_text(encoding="utf-8"):
        notes.append("já existe: " + path.name)
    else:
        writes[path] = content

# 4) launcher_preferences.xml — logo depois da "Transparência dos ícones"
xml_src = F_PREFS_XML.read_text(encoding="utf-8")
if "xaulinxs_icon_blur_enabled" in xml_src:
    notes.append("já aplicado: launcher_preferences.xml")
else:
    anchor = (
        '                android:key="xaulinxs_icon_opacity"\n'
        '                android:title="@string/xaulinxs_icon_opacity_title"\n'
        '                android:summary="@string/xaulinxs_icon_opacity_summary"\n'
        '                android:persistent="false" />\n\n'
    )
    xml_src = replace_once(xml_src, anchor, anchor + PREFS_XML_NEW, "IconOpacityPreference")
    writes[F_PREFS_XML] = xml_src

# 5) strings
str_src = F_STRINGS.read_text(encoding="utf-8")
if "xaulinxs_icon_blur_enabled_title" in str_src:
    notes.append("já aplicado: xaulinxs_strings.xml")
else:
    old_summary = ('    <string name="xaulinxs_themed_scrim_summary">Aplica um efeito de vidro fosco '
                   'temático ao papel de parede na tela de apps</string>\n')
    new_summary = ('    <string name="xaulinxs_themed_scrim_summary">Desfoca o papel de parede ao abrir/fechar '
                   'o menu de apps, com o mesmo efeito do arrasto</string>\n')
    str_src = replace_once(str_src, old_summary, new_summary, "themed_scrim_summary")
    str_src = replace_once(str_src, "</resources>", STRINGS_NEW + "</resources>", "</resources>")
    writes[F_STRINGS] = str_src


# --------------------------------------------------------------------------
# Gravação
# --------------------------------------------------------------------------

if not writes:
    print("Nada a fazer — tudo já estava aplicado.")
    for n in notes:
        print("  - " + n)
    sys.exit(0)

for path, content in writes.items():
    rel = path.relative_to(ROOT)
    if DRY:
        print("[dry-run] gravaria " + str(rel))
        continue
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print("OK  " + str(rel))

for n in notes:
    print("  - " + n)
print("\nPronto." if not DRY else "\n(dry-run: nada foi gravado)")
