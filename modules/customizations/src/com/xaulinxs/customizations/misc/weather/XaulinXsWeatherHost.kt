/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Mantém o widget de clima FIXO logo acima da barra inteligente (QSB do
 * Hotseat), só visível na página principal. Fica no DragLayer, entre o Hotseat
 * e o resto, e acompanha: posição do QSB, rolagem do Workspace (some ao ir
 * para outras páginas) e o alpha do QSB/Hotseat (some ao abrir o menu de apps).
 */
package com.xaulinxs.customizations.misc.weather

import android.view.Gravity
import android.view.View
import com.android.launcher3.InsettableFrameLayout
import com.android.launcher3.Launcher
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.misc.XaulinXsMiscPermissionActivity
import com.xaulinxs.customizations.misc.XaulinXsMiscPermissions
import com.xaulinxs.customizations.misc.XaulinXsMiscSettings

class XaulinXsWeatherHost(private val launcher: Launcher) {

    private val view = XaulinXsWeatherView(launcher)
    private val d = launcher.resources.displayMetrics.density
    private val heightPx = (116 * d).toInt()
    private val gapPx = (8 * d).toInt()
    private val permListener = Runnable { refresh(true) }

    fun attach() {
        val drag = launcher.dragLayer
        val hotseat = launcher.hotseat
        val lp = InsettableFrameLayout.LayoutParams(0, heightPx).apply {
            gravity = Gravity.TOP or Gravity.START
            ignoreInsets = true // posicionamos por coordenadas absolutas do Hotseat
        }
        drag.addView(view, drag.indexOfChild(hotseat) + 1, lp)

        hotseat.addOnLayoutChangeListener { _, _, _, _, _, _, _, _, _ -> reposition() }
        view.viewTreeObserver.addOnPreDrawListener {
            syncVisuals()
            true
        }
        // O widget é só visual: sem clique, para NUNCA roubar o toque da doca nem abrir nada.
        view.isClickable = false
        view.isLongClickable = false
        view.isFocusable = false
        view.importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
        XaulinXsMiscPermissions.addListener(permListener)
        reposition()
        syncVisuals()
    }

    fun onResume() {
        val enabled = XaulinXsMiscSettings.isWeatherEnabled(launcher)
        view.visibility = if (enabled) View.VISIBLE else View.GONE
        if (!enabled) return

        val prefs = LauncherPrefs.get(launcher)
        // Popup de ativação: uma única vez, o resto fica por conta do toque no widget.
        if (!XaulinXsMiscPermissions.hasLocation(launcher) &&
            !prefs.get(XaulinXsMiscSettings.LOCATION_PROMPT_SHOWN)
        ) {
            prefs.put(XaulinXsMiscSettings.LOCATION_PROMPT_SHOWN, true)
            XaulinXsMiscPermissionActivity.request(launcher, XaulinXsMiscPermissions.LOCATION)
        }
        refresh(false)
    }

    fun onDestroy() {
        XaulinXsMiscPermissions.removeListener(permListener)
    }

    private fun refresh(force: Boolean) {
        if (!XaulinXsMiscSettings.isWeatherEnabled(launcher)) return
        XaulinXsWeatherRepository.refresh(launcher, force) { view.state = it }
    }

    /**
     * Topo (em coordenadas do DragLayer) da parte de cima do Hotseat: o menor entre
     * o QSB e a fileira de ícones da doca. Nesta build os ícones ficam ACIMA do QSB,
     * então ancorar só no QSB colocava o widget por cima dos ícones.
     */
    private fun hotseatContentTop(): Int {
        val hotseat = launcher.hotseat
        val qsb = hotseat.qsb
        var top = hotseat.top + if (qsb != null && qsb.visibility != View.GONE && qsb.height > 0) qsb.top else hotseat.height
        val icons = hotseat.shortcutsAndWidgets
        for (i in 0 until icons.childCount) {
            val c = icons.getChildAt(i)
            if (c.visibility == View.GONE) continue
            top = minOf(top, hotseat.top + icons.top + c.top)
        }
        return top
    }

    private fun targetTranslationY(): Float =
        (hotseatContentTop() - heightPx - gapPx).toFloat() + launcher.hotseat.translationY

    /** Largura e posição X iguais às do QSB. Só roda em mudança de layout. */
    private fun reposition() {
        val hotseat = launcher.hotseat
        val qsb = hotseat.qsb ?: return
        if (qsb.width <= 0) return
        val lp = view.layoutParams
        if (lp.width != qsb.width) {
            lp.width = qsb.width
            view.layoutParams = lp
        }
        view.translationX = (hotseat.left + qsb.left).toFloat()
        view.translationY = targetTranslationY()
    }

    /** Roda a cada frame: só alpha e translação, nada que dispare novo layout. */
    private fun syncVisuals() {
        if (view.visibility != View.VISIBLE) return
        val hotseat = launcher.hotseat
        val pageFraction = launcher.workspace.xaulinXsFirstPageFraction()
        val a = pageFraction * hotseat.alpha * (hotseat.qsb?.alpha ?: 1f)
        if (view.alpha != a) view.alpha = a
        val ty = targetTranslationY()
        if (view.translationY != ty) view.translationY = ty
    }
}
