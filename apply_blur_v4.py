#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XaulinXsLauncher3 — popups v4 (aplica POR CIMA de apply_blur_v2.py + apply_blur_v3.py).

Rode na RAIZ do repositório, depois do v2 e do v3:

    python3 apply_blur_v4.py             # aplica
    python3 apply_blur_v4.py --dry-run   # só lista o que seria gravado

O que faz:

1) Popup de opções da tela inicial (área vazia: Plano de fundo / Widgets / Configurações...)
   Esse popup virou o XaulinXsOptionsSheet (AbstractSlideInView) e deixou de passar pelo
   ArrowPopup.show()/closeComplete(), que é onde o desfoque era acionado — por isso o desfoque
   "parou de funcionar". Agora o sheet aciona/desliga o mesmo XaulinXsPopupBlurHelper.

2) Desfoque da workspace INTEIRA nos dois popups
   Antes o popup só borrava workspace + hotseat (ícones e widgets). Agora o papel de parede
   também borra (mesmo raio, 70 px), com wallpaper do launcher OU do sistema.

3) Só na workspace
   O desfoque dos popups só acontece com o launcher no estado NORMAL (home). Popups de ícone
   abertos dentro do menu de aplicativos NÃO desfocam nada (o drawer tem o desfoque próprio).

4) Popup de opções do ícone rolável
   Se o conteúdo (cabeçalho + opções + atalhos) for mais alto que a tela, ele passa a rolar:
   ao rolar para baixo as opções de cima saem de vista, ao rolar para cima voltam. Um fade nas
   bordas indica que há mais conteúdo. Se couber na tela, nada muda.

Idempotente; só grava se TODAS as âncoras forem encontradas.
"""
import sys
from pathlib import Path

MARK = "XAULINXS_POPUPS_V4"
MARK_V3 = "XAULINXS_BLUR_V3"
DRY = "--dry-run" in sys.argv

ROOT = Path.cwd()
CUST = ROOT / "modules/customizations/src/com/xaulinxs/customizations"

F_HELPER = CUST / "blur/XaulinXsPopupBlurHelper.kt"
F_DEPTH = CUST / "blur/XaulinXsDepthController.kt"
F_WALLVIEW = CUST / "theme/XaulinXsWallpaperView.kt"
F_SHEET = CUST / "popup/XaulinXsOptionsSheet.kt"
F_SCROLL = CUST / "popup/XaulinXsMaxHeightScrollView.kt"
F_PCWA = ROOT / "src/com/android/launcher3/popup/PopupContainerWithArrow.kt"


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


SCROLL_KT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 * XAULINXS_POPUPS_V4
 *
 * ScrollView com altura máxima, usada pelo popup de opções do ícone
 * (PopupContainerWithArrow) quando o conteúdo é mais alto que a tela: acima do limite
 * ela rola; abaixo, se comporta como wrap_content. Fade nas bordas indica que há mais
 * conteúdo (o fade de cima só aparece depois que o usuário rola para baixo).
 */
package com.xaulinxs.customizations.popup

import android.content.Context
import android.widget.ScrollView

class XaulinXsMaxHeightScrollView(
    context: Context,
    private val maxHeightPx: Int,
) : ScrollView(context) {

    init {
        isVerticalScrollBarEnabled = false
        overScrollMode = OVER_SCROLL_NEVER
        isVerticalFadingEdgeEnabled = true
        setFadingEdgeLength((FADE_DP * resources.displayMetrics.density).toInt())
        isFillViewport = false
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val mode = MeasureSpec.getMode(heightMeasureSpec)
        val size = MeasureSpec.getSize(heightMeasureSpec)
        val limit = if (mode == MeasureSpec.UNSPECIFIED) maxHeightPx else minOf(size, maxHeightPx)
        super.onMeasure(widthMeasureSpec, MeasureSpec.makeMeasureSpec(limit, MeasureSpec.AT_MOST))
    }

    private companion object {
        const val FADE_DP = 24f
    }
}
'''

# --------------------------------------------------------------------------
# Pré-checagens
# --------------------------------------------------------------------------

for p in (F_HELPER, F_DEPTH, F_WALLVIEW, F_SHEET, F_PCWA):
    if not p.exists():
        die("não achei %s — rode o script na RAIZ do repositório." % p)

wall_src = F_WALLVIEW.read_text(encoding="utf-8")
depth_src = F_DEPTH.read_text(encoding="utf-8")
if MARK_V3 not in wall_src or MARK_V3 not in depth_src:
    die("o apply_blur_v3.py ainda não foi aplicado neste repo (rode v2, v3 e depois este).")

writes = {}
notes = []

# --------------------------------------------------------------------------
# 1) XaulinXsPopupBlurHelper.kt — só na workspace (estado NORMAL)
# --------------------------------------------------------------------------

helper_src = F_HELPER.read_text(encoding="utf-8")
if MARK in helper_src:
    notes.append("já aplicado: XaulinXsPopupBlurHelper.kt")
else:
    helper_src = replace_once(
        helper_src,
        "import com.android.launcher3.Launcher\n",
        "import com.android.launcher3.Launcher\nimport com.android.launcher3.LauncherState\n",
        "import Launcher")
    helper_src = replace_once(
        helper_src,
        "        if (!com.xaulinxs.customizations.blur.XaulinXsPopupBlur.isEnabled(launcher)) return\n",
        "        if (!com.xaulinxs.customizations.blur.XaulinXsPopupBlur.isEnabled(launcher)) return\n"
        "        // " + MARK + ": só desfoca com a workspace visível. Popup aberto no menu de aplicativos\n"
        "        // (estado ALL_APPS) não desfoca nada — o drawer já tem a função de desfoque própria.\n"
        "        if (!launcher.isInState(LauncherState.NORMAL)) return\n",
        "isEnabled")
    writes[F_HELPER] = helper_src

# --------------------------------------------------------------------------
# 2) XaulinXsDepthController.kt — o papel de parede também borra com o popup
# --------------------------------------------------------------------------

if MARK in depth_src:
    notes.append("já aplicado: XaulinXsDepthController.kt")
else:
    depth_src = replace_once(
        depth_src,
        "        applyWallpaperBlur(currentDepth * DrawerWallpaperBlurPreference.getMaxRadiusPx(launcher))\n",
        "        // " + MARK + ": com um popup aberto na workspace o wallpaper também borra (mesmo raio da\n"
        "        // workspace/hotseat); no drawer vale o maior entre o arrasto e o popup.\n"
        "        applyWallpaperBlur(\n"
        "            maxOf(currentDepth * DrawerWallpaperBlurPreference.getMaxRadiusPx(launcher), popupRadius)\n"
        "        )\n",
        "applyWallpaperBlur")
    writes[F_DEPTH] = depth_src

# --------------------------------------------------------------------------
# 3) XaulinXsWallpaperView.kt — carrega a cópia do wallpaper do sistema também p/ o popup
# --------------------------------------------------------------------------

if MARK in wall_src:
    notes.append("já aplicado: XaulinXsWallpaperView.kt")
else:
    wall_src = replace_once(
        wall_src,
        "import com.xaulinxs.customizations.settings.ThemedScrimPreference.Companion.THEMED_SCRIM_ENABLED\n",
        "import com.xaulinxs.customizations.blur.XaulinXsPopupBlur\n"
        "import com.xaulinxs.customizations.settings.ThemedScrimPreference.Companion.THEMED_SCRIM_ENABLED\n",
        "import THEMED_SCRIM_ENABLED")
    wall_src = replace_once(
        wall_src,
        "        if (!LauncherPrefs.get(context).get(THEMED_SCRIM_ENABLED)) return\n",
        "        // " + MARK + ": a cópia também serve ao desfoque dos popups (balões), não só ao do drawer.\n"
        "        val prefs = LauncherPrefs.get(context)\n"
        "        if (!prefs.get(THEMED_SCRIM_ENABLED) && !XaulinXsPopupBlur.isEnabled(context)) return\n",
        "preloadSystemWallpaperIfNeeded")
    writes[F_WALLVIEW] = wall_src

# --------------------------------------------------------------------------
# 4) XaulinXsOptionsSheet.kt — aciona e desliga o desfoque
# --------------------------------------------------------------------------

sheet_src = F_SHEET.read_text(encoding="utf-8")
if MARK in sheet_src:
    notes.append("já aplicado: XaulinXsOptionsSheet.kt")
else:
    sheet_src = replace_once(
        sheet_src,
        "import com.xaulinxs.customizations.theme.XaulinXsBalloonColor\n",
        "import com.xaulinxs.customizations.blur.XaulinXsPopupBlurHelper\n"
        "import com.xaulinxs.customizations.theme.XaulinXsBalloonColor\n",
        "import XaulinXsBalloonColor")
    sheet_src = replace_once(
        sheet_src,
        "        mIsOpen = true\n"
        "        attachToContainer()\n",
        "        mIsOpen = true\n"
        "        attachToContainer()\n"
        "        // " + MARK + ": este sheet não passa por ArrowPopup.show(), onde o desfoque era\n"
        "        // acionado. Borra workspace inteira (wallpaper + ícones + widgets) enquanto aberto.\n"
        "        XaulinXsPopupBlurHelper.onPopupShown(mActivityContext)\n",
        "openAnimated")
    sheet_src = replace_once(
        sheet_src,
        "    override fun handleClose(animate: Boolean) {\n"
        "        handleClose(animate, OPEN_CLOSE_DURATION_MS)\n"
        "    }\n",
        "    override fun handleClose(animate: Boolean) {\n"
        "        handleClose(animate, OPEN_CLOSE_DURATION_MS)\n"
        "    }\n"
        "\n"
        "    // " + MARK + ": desliga o desfoque quando o sheet termina de fechar (com ou sem animação).\n"
        "    override fun onCloseComplete() {\n"
        "        super.onCloseComplete()\n"
        "        XaulinXsPopupBlurHelper.onPopupClosed(mActivityContext)\n"
        "    }\n",
        "handleClose")
    writes[F_SHEET] = sheet_src

# --------------------------------------------------------------------------
# 5) PopupContainerWithArrow.kt — rolagem quando o conteúdo não cabe na tela
# --------------------------------------------------------------------------

pcwa_src = F_PCWA.read_text(encoding="utf-8")
if MARK in pcwa_src:
    notes.append("já aplicado: PopupContainerWithArrow.kt")
else:
    pcwa_src = replace_once(
        pcwa_src,
        "import android.widget.ImageView\n",
        "import android.widget.FrameLayout\n"
        "import android.widget.ImageView\n"
        "import android.widget.LinearLayout\n"
        "import android.widget.ScrollView\n",
        "import ImageView")
    pcwa_src = replace_once(
        pcwa_src,
        "import com.xaulinxs.customizations.theme.XaulinXsBalloonColor\n",
        "import com.xaulinxs.customizations.popup.XaulinXsMaxHeightScrollView\n"
        "import com.xaulinxs.customizations.theme.XaulinXsBalloonColor\n",
        "import XaulinXsBalloonColor")
    pcwa_src = replace_once(
        pcwa_src,
        "    private var currentHeight = 0f\n",
        "    private var currentHeight = 0f\n"
        "\n"
        "    // " + MARK + ": só existe quando o conteúdo era mais alto que a tela e foi colocado\n"
        "    // dentro de um ScrollView (ver makeScrollableIfTooTall).\n"
        "    private var scrollWrapper: ScrollView? = null\n",
        "currentHeight")
    pcwa_src = replace_once(
        pcwa_src,
        "        // Stop sending touch events to deep shortcut views if user moved beyond touch slop.\n"
        "        return (Utilities.squaredHypot(",
        "        // " + MARK + ": com rolagem ativa o gesto de arrastar é do ScrollView, não do popup.\n"
        "        if (scrollWrapper != null) return false\n"
        "        // Stop sending touch events to deep shortcut views if user moved beyond touch slop.\n"
        "        return (Utilities.squaredHypot(",
        "onInterceptTouchEvent")
    pcwa_src = replace_once(
        pcwa_src,
        "        val insets = dragLayer.insets\n"
        "        val width = measuredWidth\n"
        "        val height = measuredHeight\n",
        "        val insets = dragLayer.insets\n"
        "        // " + MARK + ": se não couber na tela, passa a rolar (e re-mede).\n"
        "        makeScrollableIfTooTall(\n"
        "            dragLayer.height - insets.top - insets.bottom - 2 * xaulinXsBottomAnchorMargin\n"
        "        )\n"
        "        val width = measuredWidth\n"
        "        val height = measuredHeight\n",
        "orientAboutObject")
    pcwa_src = replace_once(
        pcwa_src,
        "    private val xaulinXsBottomAnchorMargin: Int\n"
        "        get() = resources.getDimensionPixelSize(R.dimen.xaulinxs_app_popup_bottom_margin)\n",
        "    private val xaulinXsBottomAnchorMargin: Int\n"
        "        get() = resources.getDimensionPixelSize(R.dimen.xaulinxs_app_popup_bottom_margin)\n"
        "\n"
        "    /**\n"
        "     * " + MARK + ": se o popup (cabeçalho + opções + atalhos) for mais alto que o espaço\n"
        "     * disponível, move todos os filhos para um ScrollView com altura máxima. Rolando para\n"
        "     * baixo as opções de cima saem de vista; rolando para cima voltam. Se couber, não faz nada.\n"
        "     * Roda uma vez, antes de o popup ser exibido (o LayoutTransition só é ligado depois).\n"
        "     */\n"
        "    private fun makeScrollableIfTooTall(availablePx: Int) {\n"
        "        if (scrollWrapper != null) return\n"
        "        val chromePx = paddingTop + paddingBottom\n"
        "        if (measuredHeight <= availablePx || availablePx <= chromePx) return\n"
        "\n"
        "        val kids = ArrayList<View>(childCount)\n"
        "        for (i in 0 until childCount) kids.add(getChildAt(i))\n"
        "\n"
        "        val savedTransition = layoutTransition\n"
        "        layoutTransition = null\n"
        "        removeAllViews()\n"
        "\n"
        "        val content = LinearLayout(context).apply { orientation = LinearLayout.VERTICAL }\n"
        "        kids.forEach { content.addView(it) }\n"
        "        // Mesmas margens entre blocos que o ArrowPopup aplicaria direto nos filhos.\n"
        "        assignMarginsAndBackgrounds(content)\n"
        "\n"
        "        val scroller = XaulinXsMaxHeightScrollView(context, availablePx - chromePx)\n"
        "        scroller.addView(\n"
        "            content,\n"
        "            FrameLayout.LayoutParams(\n"
        "                ViewGroup.LayoutParams.WRAP_CONTENT,\n"
        "                ViewGroup.LayoutParams.WRAP_CONTENT,\n"
        "            ),\n"
        "        )\n"
        "        addView(\n"
        "            scroller,\n"
        "            LinearLayout.LayoutParams(\n"
        "                ViewGroup.LayoutParams.WRAP_CONTENT,\n"
        "                ViewGroup.LayoutParams.WRAP_CONTENT,\n"
        "            ),\n"
        "        )\n"
        "        layoutTransition = savedTransition\n"
        "        scrollWrapper = scroller\n"
        "        measure(View.MeasureSpec.UNSPECIFIED, View.MeasureSpec.UNSPECIFIED)\n"
        "    }\n",
        "xaulinXsBottomAnchorMargin")
    writes[F_PCWA] = pcwa_src

# --------------------------------------------------------------------------
# 6) Arquivo novo
# --------------------------------------------------------------------------

if F_SCROLL.exists() and F_SCROLL.read_text(encoding="utf-8") == SCROLL_KT:
    notes.append("já existe: " + F_SCROLL.name)
else:
    writes[F_SCROLL] = SCROLL_KT

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
