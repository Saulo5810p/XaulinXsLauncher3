#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XaulinXsLauncher3 — desfoque v2.

Rode na RAIZ do repositório:

    python3 apply_blur_v2.py             # aplica
    python3 apply_blur_v2.py --dry-run   # só lista o que seria gravado

O que faz:

1) "Fundo desfocado no menu de apps" (THEMED_SCRIM_ENABLED)
   - O véu temático colorido some (WallpaperScrimHelper devolve transparente).
   - O papel de parede (XaulinXsWallpaperView) passa a ser desfocado com a
     MESMA curva do arrasto de abrir/fechar o drawer: raio = 320px * progresso.
   - O desfoque que a workspace/hotseat já recebiam no arrasto continua
     EXATAMENTE como estava (XaulinXsDepthController intacto nessa parte);
     os dois acontecem juntos.
   - O slider "Transparência do véu temático" sai da tela de configurações
     (não tem mais véu para ajustar).

2) Nova customization "Ícones desfocados" (categoria Ícone)
   - Interruptor + slider de intensidade 0-200%.
   - Estático e INDEPENDENTE do arrasto do drawer: borra só o ícone (não o
     texto) de todo BubbleTextView — home, hotseat, pastas abertas e menu de apps.
   - Não toca em nada do efeito de abertura/fechamento do drawer.

Idempotente, e também limpa o que a versão anterior do script (V1) tenha
deixado. Nada é gravado se alguma âncora não for encontrada.
"""
import re
import subprocess
import sys
from pathlib import Path

MARK = "XAULINXS_BLUR_V2"
MARK_V1 = "XAULINXS_ICON_BLUR_V1"
DRY = "--dry-run" in sys.argv

ROOT = Path.cwd()
CUST = ROOT / "modules/customizations/src/com/xaulinxs/customizations"

F_DEPTH = CUST / "blur/XaulinXsDepthController.kt"
F_WALLVIEW = CUST / "theme/XaulinXsWallpaperView.kt"
F_SCRIM = CUST / "theme/WallpaperScrimHelper.kt"
F_ICONBLUR = CUST / "icons/XaulinXsIconBlur.kt"
F_PREF_EN = CUST / "settings/IconBlurEnabledPreference.kt"
F_PREF_PCT = CUST / "settings/IconBlurPercentPreference.kt"
F_BTV = ROOT / "src/com/android/launcher3/BubbleTextView.java"
F_PREFS_XML = ROOT / "res/xml/launcher_preferences.xml"
F_STRINGS = ROOT / "res/values/xaulinxs_strings.xml"


def die(msg):
    print("ERRO: " + msg)
    print("Nada foi alterado.")
    sys.exit(1)


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        die("âncora '%s' encontrada %d vez(es) (esperado 1). O arquivo mudou?" % (label, n))
    return text.replace(old, new)


# --------------------------------------------------------------------------
# Arquivos novos
# --------------------------------------------------------------------------

ICON_BLUR_KT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 * XAULINXS_BLUR_V2
 *
 * "Ícones desfocados": desfoque ESTÁTICO (0-200%) aplicado só ao ícone de todo
 * BubbleTextView — home, hotseat, pastas abertas e menu de apps. Não tem
 * relação nenhuma com o desfoque do arrasto de abrir/fechar o app drawer
 * (XaulinXsDepthController), que não é tocado por esta feature.
 *
 * Como funciona: BubbleTextView.applyCompoundDrawables() passa o ícone por
 * wrapIfNeeded(). Com a feature desligada (ou em 0%) devolve o próprio ícone,
 * ou seja, o comportamento é idêntico ao original. Ligada, embrulha o ícone num
 * Drawable que o desenha dentro de um RenderNode com RenderEffect de blur
 * (só o ícone; o texto do label continua nítido).
 */
package com.xaulinxs.customizations.icons

import android.content.Context
import android.graphics.Canvas
import android.graphics.ColorFilter
import android.graphics.PixelFormat
import android.graphics.Rect
import android.graphics.RenderEffect
import android.graphics.RenderNode
import android.graphics.Shader
import android.graphics.drawable.Drawable
import android.os.Build
import androidx.annotation.RequiresApi
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem
import com.android.launcher3.icons.FastBitmapDrawable

object XaulinXsIconBlur {
    private const val KEY_ICON_BLUR_ENABLED = "xaulinxs_icon_blur_enabled"
    private const val KEY_ICON_BLUR_PERCENT = "xaulinxs_icon_blur_percent"

    const val MIN_PERCENT = 0
    const val MAX_PERCENT = 200
    const val DEFAULT_PERCENT = 100

    // Raio do desfoque a 100%, em dp (200% = o dobro). É a única constante a
    // mexer se quiser o desfoque dos ícones mais forte ou mais fraco.
    const val BASE_RADIUS_DP = 6f

    // Desligado por padrão: nada muda visualmente até o usuário ligar.
    @JvmField
    val ICON_BLUR_ENABLED = backedUpItem(KEY_ICON_BLUR_ENABLED, false)

    @JvmField
    val ICON_BLUR_PERCENT = backedUpItem(KEY_ICON_BLUR_PERCENT, DEFAULT_PERCENT)

    /** Raio atual em px; 0 se desligado, 0%, ou Android < 12. */
    @JvmStatic
    fun getRadiusPx(context: Context): Float {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return 0f
        val prefs = LauncherPrefs.get(context)
        if (!prefs.get(ICON_BLUR_ENABLED)) return 0f
        val percent = prefs.get(ICON_BLUR_PERCENT).coerceIn(MIN_PERCENT, MAX_PERCENT)
        return BASE_RADIUS_DP * context.resources.displayMetrics.density * percent / 100f
    }

    /** Chamado por BubbleTextView.applyCompoundDrawables(). */
    @JvmStatic
    fun wrapIfNeeded(context: Context, icon: Drawable): Drawable {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return icon
        // Só ícones reais; o ColorDrawable transparente de "ícone oculto" fica como está.
        if (icon !is FastBitmapDrawable) return icon
        val radiusPx = getRadiusPx(context)
        if (radiusPx < 1f) return icon
        val wrapper = XaulinXsBlurIconDrawable(icon, radiusPx)
        // O TextView lê os bounds do drawable ao medir; o wrapper nasce com os do ícone.
        wrapper.setBounds(icon.bounds)
        return wrapper
    }
}

@RequiresApi(Build.VERSION_CODES.S)
class XaulinXsBlurIconDrawable(
    private val inner: Drawable,
    private val radiusPx: Float,
) : Drawable(), Drawable.Callback {

    private val node = RenderNode("xaulinxs_icon_blur")
    private val padPx = Math.ceil((radiusPx * 3f).toDouble()).toInt()

    init {
        inner.setCallback(this)
        node.setRenderEffect(
            RenderEffect.createBlurEffect(radiusPx, radiusPx, Shader.TileMode.CLAMP)
        )
    }

    override fun onBoundsChange(bounds: Rect) {
        inner.setBounds(bounds)
    }

    override fun draw(canvas: Canvas) {
        val b = bounds
        if (b.isEmpty || !canvas.isHardwareAccelerated) {
            // Canvas de software (ex.: render em Bitmap): sem RenderEffect, desenha normal.
            inner.draw(canvas)
            return
        }
        // O RenderNode é maior que o ícone (padPx de cada lado) para o blur não ser cortado.
        val w = b.width() + 2 * padPx
        val h = b.height() + 2 * padPx
        node.setPosition(0, 0, w, h)
        val rc = node.beginRecording(w, h)
        try {
            rc.translate((padPx - b.left).toFloat(), (padPx - b.top).toFloat())
            inner.draw(rc)
        } finally {
            node.endRecording()
        }
        val count = canvas.save()
        canvas.translate((b.left - padPx).toFloat(), (b.top - padPx).toFloat())
        canvas.drawRenderNode(node)
        canvas.restoreToCount(count)
    }

    override fun setAlpha(alpha: Int) {
        inner.setAlpha(alpha)
    }

    override fun getAlpha(): Int = inner.getAlpha()

    override fun setColorFilter(colorFilter: ColorFilter?) {
        inner.setColorFilter(colorFilter)
    }

    @Suppress("DEPRECATION")
    override fun getOpacity(): Int = PixelFormat.TRANSLUCENT

    override fun getIntrinsicWidth(): Int = inner.intrinsicWidth

    override fun getIntrinsicHeight(): Int = inner.intrinsicHeight

    override fun isStateful(): Boolean = inner.isStateful

    override fun onStateChange(state: IntArray): Boolean = inner.setState(state)

    override fun onLevelChange(level: Int): Boolean = inner.setLevel(level)

    override fun setVisible(visible: Boolean, restart: Boolean): Boolean {
        inner.setVisible(visible, restart)
        return super.setVisible(visible, restart)
    }

    override fun invalidateDrawable(who: Drawable) {
        invalidateSelf()
    }

    override fun scheduleDrawable(who: Drawable, what: Runnable, `when`: Long) {
        scheduleSelf(what, `when`)
    }

    override fun unscheduleDrawable(who: Drawable, what: Runnable) {
        unscheduleSelf(what)
    }
}
'''

PREF_ENABLED_KT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 * XAULINXS_BLUR_V2
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherAppState
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
            LauncherPrefs.get(context).put(XaulinXsIconBlur.ICON_BLUR_ENABLED, newValue as Boolean)
            // Mesmo padrão da opacidade dos ícones: rebinda todos os ícones já na tela.
            LauncherAppState.getInstance(context).model.forceReload("xaulinxs_icon_blur_toggle")
            true
        }
    }
}
'''

PREF_PERCENT_KT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 * XAULINXS_BLUR_V2
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.LauncherAppState
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
            LauncherAppState.getInstance(context).model.forceReload("xaulinxs_icon_blur_percent")
            true
        }
    }
}
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

STRINGS = {
    "xaulinxs_themed_scrim_summary":
        "Desfoca o papel de parede ao abrir/fechar o menu de apps, com o mesmo efeito de desfoque do arrasto",
    "xaulinxs_icon_blur_enabled_title": "Ícones desfocados",
    "xaulinxs_icon_blur_enabled_summary": "Desfoca os ícones na tela inicial e no menu de apps",
    "xaulinxs_icon_blur_percent_title": "Intensidade do desfoque dos ícones",
    "xaulinxs_icon_blur_percent_summary": "0% a 200% (100% = intensidade padrão)",
}


def upsert_string(text, name, value):
    line = '    <string name="%s">%s</string>\n' % (name, value)
    pat = re.compile(r'^[ \t]*<string name="%s">[^\n]*</string>[ \t]*\n' % re.escape(name), re.M)
    if pat.search(text):
        return pat.sub(lambda m: line, text, count=1)
    if text.count("</resources>") != 1:
        die("strings: '</resources>' não encontrado exatamente uma vez.")
    return text.replace("</resources>", line + "</resources>")


# --------------------------------------------------------------------------
# Pré-checagens
# --------------------------------------------------------------------------

for p in (F_DEPTH, F_WALLVIEW, F_SCRIM, F_BTV, F_PREFS_XML, F_STRINGS):
    if not p.exists():
        die("não achei %s — rode o script na RAIZ do repositório." % p)

writes = {}
notes = []


def rel(p):
    return str(p.relative_to(ROOT))


# --------------------------------------------------------------------------
# 1) XaulinXsDepthController.kt — acrescenta o desfoque do wallpaper
#    (a parte da workspace/hotseat/balão não é alterada)
# --------------------------------------------------------------------------

depth_src = F_DEPTH.read_text(encoding="utf-8")
if MARK_V1 in depth_src:
    # A V1 reescreveu este arquivo inteiro; volta ao original do último commit.
    r = subprocess.run(["git", "show", "HEAD:" + rel(F_DEPTH)], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        die("achei resíduo da V1 em XaulinXsDepthController.kt e não consegui ler o original via git. "
            "Rode `git checkout -- " + rel(F_DEPTH) + "` e rode este script de novo.")
    depth_src = r.stdout
    notes.append("V1 detectada em XaulinXsDepthController.kt: voltou ao original do HEAD")

if "applyWallpaperBlur" in depth_src:
    notes.append("já aplicado: XaulinXsDepthController.kt")
else:
    if "DRAWER_MAX_BLUR_RADIUS_PX" not in depth_src or "private fun applyEffectiveBlur" not in depth_src:
        die("XaulinXsDepthController.kt não tem o formato esperado.")
    depth_src = replace_once(
        depth_src,
        "import android.view.WindowManager\n",
        "import android.view.View\nimport android.view.WindowManager\n",
        "import WindowManager")
    depth_src = replace_once(
        depth_src,
        "import com.android.launcher3.Launcher\n",
        "import com.android.launcher3.Launcher\n"
        "import com.android.launcher3.R\n"
        "import com.xaulinxs.customizations.theme.XaulinXsWallpaperView\n",
        "import Launcher")
    depth_src = replace_once(
        depth_src,
        "    private var appliedRadius = -1f\n",
        "    private var appliedRadius = -1f\n"
        "\n"
        "    // " + MARK + ": desfoque do papel de parede (XaulinXsWallpaperView), mesma curva do arrasto.\n"
        "    private var appliedWallpaperRadius = -1\n"
        "    private var wallpaperView: XaulinXsWallpaperView? = null\n",
        "appliedRadius")
    depth_src = replace_once(
        depth_src,
        "        val popupRadius = if (popupBlurActive) POPUP_BLUR_RADIUS_PX else 0f\n"
        "        applyBlurRadius(maxOf(drawerRadius, popupRadius))\n"
        "    }\n",
        "        val popupRadius = if (popupBlurActive) POPUP_BLUR_RADIUS_PX else 0f\n"
        "        // " + MARK + ": o wallpaper acompanha só o arrasto do drawer (0..320px), não o balão.\n"
        "        applyWallpaperBlur(drawerRadius)\n"
        "        applyBlurRadius(maxOf(drawerRadius, popupRadius))\n"
        "    }\n"
        "\n"
        "    private fun applyWallpaperBlur(radiusPx: Float) {\n"
        "        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return\n"
        "        val radius = radiusPx.toInt()\n"
        "        if (radius == appliedWallpaperRadius) return\n"
        "        appliedWallpaperRadius = radius\n"
        "        findWallpaperView()?.setDepthBlurRadiusPx(radius.toFloat())\n"
        "    }\n"
        "\n"
        "    private fun findWallpaperView(): XaulinXsWallpaperView? {\n"
        "        if (wallpaperView == null) {\n"
        "            val v: View? = launcher.findViewById(R.id.xaulinxs_wallpaper_view)\n"
        "            wallpaperView = v as? XaulinXsWallpaperView\n"
        "        }\n"
        "        return wallpaperView\n"
        "    }\n",
        "applyEffectiveBlur")
    writes[F_DEPTH] = depth_src

# --------------------------------------------------------------------------
# 2) XaulinXsWallpaperView.kt — raio vindo do arrasto, somado ao desfoque fixo
# --------------------------------------------------------------------------

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
        "onEnabledPrefChanged")
    wall_src = replace_once(
        wall_src,
        "        val radiusPx = XaulinXsWorkspaceBlur.getBlurRadiusPx(context)\n",
        "        val radiusPx = maxOf(XaulinXsWorkspaceBlur.getBlurRadiusPx(context), depthBlurRadiusPx)\n",
        "getBlurRadiusPx")
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
        "isInAppWallpaperEnabled")
    writes[F_WALLVIEW] = wall_src

# --------------------------------------------------------------------------
# 3) WallpaperScrimHelper.kt — remove o véu temático
# --------------------------------------------------------------------------

scrim_src = F_SCRIM.read_text(encoding="utf-8")
if MARK in scrim_src:
    notes.append("já aplicado: WallpaperScrimHelper.kt")
else:
    scrim_src = replace_once(
        scrim_src,
        "        if (prefs.get(THEMED_SCRIM_ENABLED)) return getScrimColor(context)\n",
        "        // " + MARK + ": sem véu temático. Com o desfoque ligado o fundo fica transparente\n"
        "        // para o wallpaper desfocado (XaulinXsDepthController) aparecer por trás do drawer.\n"
        "        if (prefs.get(THEMED_SCRIM_ENABLED)) return android.graphics.Color.TRANSPARENT\n",
        "getScrimColor")
    writes[F_SCRIM] = scrim_src

# --------------------------------------------------------------------------
# 4) BubbleTextView.java — um único ponto de gancho
# --------------------------------------------------------------------------

btv_src = F_BTV.read_text(encoding="utf-8")
if "XaulinXsIconBlur" in btv_src:
    notes.append("já aplicado: BubbleTextView.java")
else:
    btv_src = replace_once(
        btv_src,
        "        icon.setAlpha(com.xaulinxs.customizations.icons.XaulinXsIconOpacity.getAlpha(getContext()));\n"
        "\n"
        "        updateIcon(icon);\n",
        "        icon.setAlpha(com.xaulinxs.customizations.icons.XaulinXsIconOpacity.getAlpha(getContext()));\n"
        "\n"
        "        // " + MARK + ": \"Ícones desfocados\" (estático, independente do arrasto do drawer).\n"
        "        // Desligado/0% devolve o próprio ícone, sem nenhuma mudança.\n"
        "        updateIcon(com.xaulinxs.customizations.icons.XaulinXsIconBlur.wrapIfNeeded(\n"
        "                getContext(), icon));\n",
        "applyCompoundDrawables")
    writes[F_BTV] = btv_src

# --------------------------------------------------------------------------
# 5) Arquivos Kotlin novos (sempre regravados se o conteúdo diferir)
# --------------------------------------------------------------------------

for path, content in ((F_ICONBLUR, ICON_BLUR_KT), (F_PREF_EN, PREF_ENABLED_KT), (F_PREF_PCT, PREF_PERCENT_KT)):
    if path.exists() and path.read_text(encoding="utf-8") == content:
        notes.append("já existe: " + path.name)
    else:
        writes[path] = content

# --------------------------------------------------------------------------
# 6) launcher_preferences.xml — entra o par de ícones; sai o slider do véu
# --------------------------------------------------------------------------

xml_src = F_PREFS_XML.read_text(encoding="utf-8")
xml_new = xml_src

if "xaulinxs_icon_blur_enabled" not in xml_new:
    anchor = (
        '                android:key="xaulinxs_icon_opacity"\n'
        '                android:title="@string/xaulinxs_icon_opacity_title"\n'
        '                android:summary="@string/xaulinxs_icon_opacity_summary"\n'
        '                android:persistent="false" />\n\n'
    )
    xml_new = replace_once(xml_new, anchor, anchor + PREFS_XML_NEW, "IconOpacityPreference")

scrim_block = re.compile(
    r'[ \t]*<com\.xaulinxs\.customizations\.settings\.ScrimOpacityPreference\b.*?/>[ \t]*\n(?:[ \t]*\n)?',
    re.S)
if scrim_block.search(xml_new):
    xml_new = scrim_block.sub("", xml_new, count=1)

if xml_new != xml_src:
    writes[F_PREFS_XML] = xml_new
else:
    notes.append("já aplicado: launcher_preferences.xml")

# --------------------------------------------------------------------------
# 7) strings
# --------------------------------------------------------------------------

str_src = F_STRINGS.read_text(encoding="utf-8")
str_new = str_src
for name, value in STRINGS.items():
    str_new = upsert_string(str_new, name, value)
if str_new != str_src:
    writes[F_STRINGS] = str_new
else:
    notes.append("já aplicado: xaulinxs_strings.xml")

# --------------------------------------------------------------------------
# Gravação
# --------------------------------------------------------------------------

if not writes:
    print("Nada a fazer — tudo já estava aplicado.")
    for n in notes:
        print("  - " + n)
    sys.exit(0)

for path, content in writes.items():
    if DRY:
        print("[dry-run] gravaria " + rel(path))
        continue
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print("OK  " + rel(path))

for n in notes:
    print("  - " + n)
print("\n(dry-run: nada foi gravado)" if DRY else "\nPronto.")
