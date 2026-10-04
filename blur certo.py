#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XaulinXsLauncher3 — desfoque v3 (aplica POR CIMA do apply_blur_v2.py).

Rode na RAIZ do repositório, depois do v2:

    python3 apply_blur_v3.py             # aplica
    python3 apply_blur_v3.py --dry-run   # só lista o que seria gravado

O que faz:

1) Desfoque do papel de parede com o menu de apps nos DOIS casos:
   - Wallpaper do Launcher ligado: como já estava (RenderEffect na XaulinXsWallpaperView).
   - Wallpaper do sistema (interruptor "usar wallpaper do app" desligado): o wallpaper
     do sistema é desenhado pela janela do SystemUI, fora do alcance de qualquer
     RenderEffect, e o blur de janela (cross-window blur) é bloqueado pelo ROM deste
     aparelho. Então, enquanto o drawer está sendo arrastado/aberto, a
     XaulinXsWallpaperView desenha uma CÓPIA do wallpaper do sistema (lida via
     WallpaperManager) e borra essa cópia. Com o drawer fechado a view volta a não
     desenhar nada e o wallpaper real (inclusive parallax) aparece normalmente.

2) Novo slider na categoria "Menu de aplicativo": "Intensidade do desfoque do papel
   de parede", 0 a 320 px (padrão 320 = como era). Vale para os dois casos acima.
   O desfoque da workspace/hotseat no arrasto NÃO é alterado pelo slider.

Idempotente; só grava se TODAS as âncoras forem encontradas.
"""
import re
import sys
from pathlib import Path

MARK = "XAULINXS_BLUR_V3"
MARK_V2 = "XAULINXS_BLUR_V2"
DRY = "--dry-run" in sys.argv

ROOT = Path.cwd()
CUST = ROOT / "modules/customizations/src/com/xaulinxs/customizations"

F_DEPTH = CUST / "blur/XaulinXsDepthController.kt"
F_WALLVIEW = CUST / "theme/XaulinXsWallpaperView.kt"
F_SNAPSHOT = CUST / "theme/XaulinXsSystemWallpaperSnapshot.kt"
F_PREF = CUST / "settings/DrawerWallpaperBlurPreference.kt"
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


def rel(p):
    return str(p.relative_to(ROOT))


SNAPSHOT_KT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 * XAULINXS_BLUR_V3
 *
 * Cópia (snapshot) do wallpaper ATUAL DO SISTEMA, usada só para poder desfocá-lo
 * quando o wallpaper próprio do launcher está desligado.
 *
 * Por quê: o wallpaper do sistema não é desenhado pela janela do Launcher (é a
 * janela de wallpaper do SystemUI), então RenderEffect não alcança; e o blur de
 * janela (FLAG_BLUR_BEHIND) está bloqueado pelo ROM deste aparelho. A saída é
 * desenhar nós mesmos uma cópia da imagem enquanto o drawer está aberto/arrastando
 * (XaulinXsWallpaperView) e borrar essa cópia.
 *
 * Limitações conhecidas:
 *  - Precisa conseguir LER o wallpaper: WallpaperManager.getDrawable() exige
 *    "Acesso a todos os arquivos" (MANAGE_EXTERNAL_STORAGE, já declarada no manifest,
 *    mesma permissão usada pelas fontes). Sem ela, a leitura falha em silêncio
 *    (log "XaulinXsSysWallpaper") e simplesmente não há desfoque nesse modo.
 *  - Wallpaper animado (live wallpaper) não tem imagem estática: sem desfoque.
 */
package com.xaulinxs.customizations.theme

import android.app.WallpaperManager
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.drawable.BitmapDrawable
import android.os.SystemClock
import android.util.Log
import com.android.launcher3.util.Executors

object XaulinXsSystemWallpaperSnapshot {
    private const val TAG = "XaulinXsSysWallpaper"
    private const val RETRY_AFTER_FAILURE_MS = 10_000L

    @Volatile private var bitmap: Bitmap? = null
    @Volatile private var loadedId = -1
    @Volatile private var loading = false
    @Volatile private var lastFailureAt = 0L

    /** Snapshot já carregado (ou null). Seguro de chamar em onDraw. */
    @JvmStatic
    fun peek(): Bitmap? = bitmap

    /**
     * Garante, em background, que o snapshot do wallpaper atual do sistema esteja
     * carregado. [onReady] roda na main thread quando um bitmap novo ficar pronto.
     */
    @JvmStatic
    fun ensureLoaded(context: Context, onReady: () -> Unit) {
        val app = context.applicationContext
        val wm = WallpaperManager.getInstance(app)
        val id = try {
            wm.getWallpaperId(WallpaperManager.FLAG_SYSTEM)
        } catch (e: Exception) {
            -1
        }
        if (bitmap != null && id == loadedId) return
        if (loading) return
        if (lastFailureAt != 0L &&
            SystemClock.elapsedRealtime() - lastFailureAt < RETRY_AFTER_FAILURE_MS
        ) return

        loading = true
        Executors.THREAD_POOL_EXECUTOR.execute {
            try {
                if (wm.wallpaperInfo != null) {
                    // Live wallpaper: não existe imagem estática confiável para borrar.
                    bitmap = null
                    loadedId = id
                    lastFailureAt = SystemClock.elapsedRealtime()
                    return@execute
                }
                val d = wm.drawable
                val bmp = when {
                    d == null -> null
                    d is BitmapDrawable -> d.bitmap
                    else -> {
                        val w = d.intrinsicWidth.coerceAtLeast(1)
                        val h = d.intrinsicHeight.coerceAtLeast(1)
                        Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888).also {
                            d.setBounds(0, 0, w, h)
                            d.draw(Canvas(it))
                        }
                    }
                }
                bitmap = bmp
                loadedId = id
                if (bmp != null) {
                    lastFailureAt = 0L
                    Executors.MAIN_EXECUTOR.execute(onReady)
                } else {
                    lastFailureAt = SystemClock.elapsedRealtime()
                }
            } catch (e: SecurityException) {
                lastFailureAt = SystemClock.elapsedRealtime()
                Log.w(TAG, "Sem permissão para ler o wallpaper do sistema " +
                    "(conceda 'Acesso a todos os arquivos' ao launcher)", e)
            } catch (e: Exception) {
                lastFailureAt = SystemClock.elapsedRealtime()
                Log.w(TAG, "Falha ao ler o wallpaper do sistema", e)
            } finally {
                loading = false
            }
        }
    }
}
'''

PREF_KT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 * XAULINXS_BLUR_V3
 *
 * Slider "Intensidade do desfoque do papel de parede" (categoria Menu de aplicativo).
 * Define o raio MÁXIMO (0 a 320 px) que o papel de parede alcança com o drawer
 * totalmente aberto; durante o arrasto o raio cresce de 0 até esse valor.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

class DrawerWallpaperBlurPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = MIN_PX
        max = MAX_PX
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(DRAWER_WALLPAPER_BLUR_PX).coerceIn(MIN_PX, MAX_PX)
        setOnPreferenceChangeListener { _, newValue ->
            // Lido a cada frame do próximo arrasto do drawer; não precisa forçar nada.
            LauncherPrefs.get(context).put(DRAWER_WALLPAPER_BLUR_PX, newValue as Int)
            true
        }
    }

    companion object {
        const val MIN_PX = 0
        const val MAX_PX = 320
        private const val KEY_DRAWER_WALLPAPER_BLUR_PX = "xaulinxs_drawer_wallpaper_blur_px"

        // Padrão 320 = intensidade que o desfoque sempre teve.
        val DRAWER_WALLPAPER_BLUR_PX = backedUpItem(KEY_DRAWER_WALLPAPER_BLUR_PX, MAX_PX)

        /** Raio máximo (px) do desfoque do wallpaper com o drawer aberto. */
        fun getMaxRadiusPx(context: Context): Float =
            LauncherPrefs.get(context).get(DRAWER_WALLPAPER_BLUR_PX)
                .coerceIn(MIN_PX, MAX_PX).toFloat()
    }
}
'''

PREF_XML_NEW = '''            <com.xaulinxs.customizations.settings.DrawerWallpaperBlurPreference
                android:key="xaulinxs_drawer_wallpaper_blur"
                android:title="@string/xaulinxs_drawer_wallpaper_blur_title"
                android:summary="@string/xaulinxs_drawer_wallpaper_blur_summary"
                android:dependency="xaulinxs_themed_scrim"
                android:persistent="false" />

'''

STRINGS = {
    "xaulinxs_drawer_wallpaper_blur_title": "Intensidade do desfoque do papel de parede",
    "xaulinxs_drawer_wallpaper_blur_summary":
        "0 a 320 px — o quanto o papel de parede desfoca com o menu de apps aberto "
        "(wallpaper do launcher ou do sistema)",
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

for p in (F_DEPTH, F_WALLVIEW, F_PREFS_XML, F_STRINGS):
    if not p.exists():
        die("não achei %s — rode o script na RAIZ do repositório." % p)

writes = {}
notes = []

wall_src = F_WALLVIEW.read_text(encoding="utf-8")
depth_src = F_DEPTH.read_text(encoding="utf-8")

if "setDepthBlurRadiusPx" not in wall_src or MARK_V2 not in depth_src:
    die("o apply_blur_v2.py ainda não foi aplicado neste repo. Rode-o primeiro e depois este.")

# --------------------------------------------------------------------------
# 1) XaulinXsWallpaperView.kt
# --------------------------------------------------------------------------

if MARK in wall_src:
    notes.append("já aplicado: XaulinXsWallpaperView.kt")
else:
    wall_src = replace_once(
        wall_src,
        "import com.android.launcher3.LauncherPrefs\n",
        "import com.android.launcher3.LauncherPrefs\n"
        "import com.xaulinxs.customizations.settings.ThemedScrimPreference.Companion.THEMED_SCRIM_ENABLED\n",
        "import LauncherPrefs")

    wall_src = replace_once(
        wall_src,
        "    private val onEnabledPrefChanged: () -> Unit = { post { applyBlurEffect(); invalidate() } }\n",
        "    private val onEnabledPrefChanged: () -> Unit =\n"
        "        { post { applyBlurEffect(); preloadSystemWallpaperIfNeeded(); invalidate() } }\n"
        "\n"
        "    // " + MARK + ": pincel da cópia do wallpaper do sistema (alpha varia no fade-in).\n"
        "    private val systemPaint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)\n",
        "onEnabledPrefChanged")

    wall_src = replace_once(
        wall_src,
        "        XaulinXsInAppWallpaperSetting.addOnChangedListener(onEnabledPrefChanged)\n"
        "        applyBlurEffect()\n",
        "        XaulinXsInAppWallpaperSetting.addOnChangedListener(onEnabledPrefChanged)\n"
        "        applyBlurEffect()\n"
        "        preloadSystemWallpaperIfNeeded()\n",
        "onAttachedToWindow")

    # Desfoque do drawer vale com wallpaper do app OU do sistema.
    wall_src = replace_once(
        wall_src,
        "        if (!isInAppWallpaperEnabled()) {\n"
        "            setRenderEffect(null)\n"
        "            return\n"
        "        }\n"
        "        val radiusPx = maxOf(XaulinXsWorkspaceBlur.getBlurRadiusPx(context), depthBlurRadiusPx)\n",
        "        // " + MARK + ": com o wallpaper do app desligado, o desfoque do drawer continua valendo —\n"
        "        // aplicado à cópia do wallpaper do sistema (ver onDraw). O desfoque fixo da tela inicial\n"
        "        // segue valendo só para o wallpaper do app.\n"
        "        val radiusPx = if (isInAppWallpaperEnabled()) {\n"
        "            maxOf(XaulinXsWorkspaceBlur.getBlurRadiusPx(context), depthBlurRadiusPx)\n"
        "        } else {\n"
        "            depthBlurRadiusPx\n"
        "        }\n",
        "applyBlurEffect")

    wall_src = replace_once(
        wall_src,
        "        depthBlurRadiusPx = radiusPx\n"
        "        applyBlurEffect()\n"
        "    }\n"
        "\n"
        "    private fun isInAppWallpaperEnabled(): Boolean =\n",
        "        depthBlurRadiusPx = radiusPx\n"
        "        applyBlurEffect()\n"
        "        if (!isInAppWallpaperEnabled()) {\n"
        "            if (radiusPx > 0f) preloadSystemWallpaperIfNeeded()\n"
        "            invalidate() // o fade-in da cópia depende do raio, então redesenha\n"
        "        }\n"
        "    }\n"
        "\n"
        "    /** " + MARK + ": carrega (em background) a cópia do wallpaper do sistema, se for preciso. */\n"
        "    private fun preloadSystemWallpaperIfNeeded() {\n"
        "        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return\n"
        "        if (isInAppWallpaperEnabled()) return\n"
        "        if (!LauncherPrefs.get(context).get(THEMED_SCRIM_ENABLED)) return\n"
        "        XaulinXsSystemWallpaperSnapshot.ensureLoaded(context) { invalidate() }\n"
        "    }\n"
        "\n"
        "    /**\n"
        "     * " + MARK + ": só enquanto o drawer está sendo aberto/arrastado desenha a cópia do wallpaper\n"
        "     * do sistema (center-crop) por cima do wallpaper real, que passa a ser borrada pelo\n"
        "     * RenderEffect desta view. Com o drawer fechado (raio 0) não desenha nada.\n"
        "     */\n"
        "    private fun drawSystemWallpaperSnapshot(canvas: Canvas) {\n"
        "        val radius = depthBlurRadiusPx\n"
        "        if (radius < 1f) return\n"
        "        val bitmap = XaulinXsSystemWallpaperSnapshot.peek() ?: return\n"
        "        val viewW = width.toFloat()\n"
        "        val viewH = height.toFloat()\n"
        "        if (viewW <= 0f || viewH <= 0f) return\n"
        "        val bmpW = bitmap.width.toFloat()\n"
        "        val bmpH = bitmap.height.toFloat()\n"
        "        val scale = maxOf(viewW / bmpW, viewH / bmpH)\n"
        "        matrix.reset()\n"
        "        matrix.setScale(scale, scale)\n"
        "        matrix.postTranslate((viewW - bmpW * scale) / 2f, (viewH - bmpH * scale) / 2f)\n"
        "        // Fade-in nos primeiros pixels de raio: esconde qualquer diferença de enquadramento\n"
        "        // entre a cópia e o wallpaper real no instante em que a cópia aparece.\n"
        "        systemPaint.alpha = (255f * (radius / SNAPSHOT_FADE_IN_PX).coerceIn(0f, 1f)).toInt()\n"
        "        canvas.drawBitmap(bitmap, matrix, systemPaint)\n"
        "    }\n"
        "\n"
        "    private fun isInAppWallpaperEnabled(): Boolean =\n",
        "setDepthBlurRadiusPx")

    wall_src = replace_once(
        wall_src,
        "        if (!isInAppWallpaperEnabled()) {\n"
        "            // Interruptor desligado: não pintar nada, de propósito — o\n"
        "            // wallpaper real do sistema (por trás desta janela) aparece.\n"
        "            return\n"
        "        }\n",
        "        if (!isInAppWallpaperEnabled()) {\n"
        "            // Interruptor desligado: não pintar nada, de propósito — o wallpaper real do\n"
        "            // sistema (por trás desta janela) aparece. Única exceção: durante o desfoque do\n"
        "            // drawer, desenha a cópia borrada do wallpaper do sistema (" + MARK + ").\n"
        "            drawSystemWallpaperSnapshot(canvas)\n"
        "            return\n"
        "        }\n",
        "onDraw")

    wall_src = replace_once(
        wall_src,
        "        const val FALLBACK_COLOR = Color.BLACK\n",
        "        const val FALLBACK_COLOR = Color.BLACK\n"
        "        const val SNAPSHOT_FADE_IN_PX = 48f\n",
        "FALLBACK_COLOR")

    writes[F_WALLVIEW] = wall_src

# --------------------------------------------------------------------------
# 2) XaulinXsDepthController.kt — wallpaper usa o slider; resto intacto
# --------------------------------------------------------------------------

if MARK in depth_src:
    notes.append("já aplicado: XaulinXsDepthController.kt")
else:
    depth_src = replace_once(
        depth_src,
        "import com.xaulinxs.customizations.theme.XaulinXsWallpaperView\n",
        "import com.xaulinxs.customizations.settings.DrawerWallpaperBlurPreference\n"
        "import com.xaulinxs.customizations.theme.XaulinXsWallpaperView\n",
        "import XaulinXsWallpaperView")
    depth_src = replace_once(
        depth_src,
        "        applyWallpaperBlur(drawerRadius)\n",
        "        // " + MARK + ": intensidade do wallpaper vem do slider do Menu de aplicativo (0..320 px);\n"
        "        // workspace/hotseat/janela seguem com 320 px fixos, como sempre.\n"
        "        applyWallpaperBlur(currentDepth * DrawerWallpaperBlurPreference.getMaxRadiusPx(launcher))\n",
        "applyWallpaperBlur")
    writes[F_DEPTH] = depth_src

# --------------------------------------------------------------------------
# 3) Arquivos novos
# --------------------------------------------------------------------------

for path, content in ((F_SNAPSHOT, SNAPSHOT_KT), (F_PREF, PREF_KT)):
    if path.exists() and path.read_text(encoding="utf-8") == content:
        notes.append("já existe: " + path.name)
    else:
        writes[path] = content

# --------------------------------------------------------------------------
# 4) launcher_preferences.xml — slider logo abaixo do interruptor do desfoque
# --------------------------------------------------------------------------

xml_src = F_PREFS_XML.read_text(encoding="utf-8")
if "xaulinxs_drawer_wallpaper_blur" in xml_src:
    notes.append("já aplicado: launcher_preferences.xml")
else:
    anchor = (
        '                android:summary="@string/xaulinxs_themed_scrim_summary"\n'
        '                android:persistent="false" />\n\n'
    )
    writes[F_PREFS_XML] = replace_once(xml_src, anchor, anchor + PREF_XML_NEW, "ThemedScrimPreference")

# --------------------------------------------------------------------------
# 5) strings
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
