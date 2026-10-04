/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Implementa o desfoque real ("vidro fosco") do App Drawer sem depender do
 * flavor Quickstep. O AOSP tem um DepthController completo em
 * quickstep/src/.../statehandlers/DepthController.java, mas ele exige o
 * SystemUiProxy — dependência exclusiva de builds com Quickstep. Esta é
 * uma implementação independente, usando RenderEffect e FLAG_BLUR_BEHIND —
 * a mesma técnica que o AOSP já usa em
 * com.android.launcher3.organizer.creation.screen.ui.BlurController.
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
import com.android.launcher3.R
import com.xaulinxs.customizations.settings.DrawerWallpaperBlurPreference
import com.xaulinxs.customizations.theme.XaulinXsWallpaperView
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.settings.ThemedScrimPreference.Companion.THEMED_SCRIM_ENABLED

// Raio do blur do App Drawer, sincronizado com o progresso do gesto de
// abrir/fechar (0..1 * este valor). 320px (~128dp em xxhdpi) — intensidade
// forte pedida para o vidro fosco do drawer.
private const val DRAWER_MAX_BLUR_RADIUS_PX = 320f

// Raio do blur atrás de um balão de contexto (long-press), aplicado de forma
// instantânea (sem crescer a partir de um gesto) — diferente do drawer, aqui
// não há transição progressiva, então um raio muito alto aplicado de uma vez
// gera artefato visual (a View borrada "some" em vez de ficar fosca).
private const val POPUP_BLUR_RADIUS_PX = 70f

private const val TAG = "XaulinXsDepthController"

class XaulinXsDepthController(private val launcher: Launcher) {

    private var currentDepth = 0f
    private var popupBlurActive = false
    private var appliedRadius = -1f

    // XAULINXS_BLUR_V2: desfoque do papel de parede (XaulinXsWallpaperView), mesma curva do arrasto.
    private var appliedWallpaperRadius = -1
    private var wallpaperView: XaulinXsWallpaperView? = null

    private val isEnabled: Boolean
        get() = LauncherPrefs.get(launcher).get(THEMED_SCRIM_ENABLED)

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

    fun setDepth(depth: Float) {
        val clamped = depth.coerceIn(0f, 1f)
        currentDepth = if (isEnabled) clamped else 0f
        XaulinXsWindowBlurStateHolder.setBlurEnabled(
            isEnabled && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S
        )
        applyEffectiveBlur()
    }

    fun setPopupBlurActive(active: Boolean) {
        if (popupBlurActive == active) return
        popupBlurActive = active
        applyEffectiveBlur()
    }

    private fun applyEffectiveBlur() {
        val drawerRadius = currentDepth * DRAWER_MAX_BLUR_RADIUS_PX
        val popupRadius = if (popupBlurActive) POPUP_BLUR_RADIUS_PX else 0f
        // XAULINXS_BLUR_V2: o wallpaper acompanha só o arrasto do drawer (0..320px), não o balão.
        // XAULINXS_BLUR_V3: intensidade do wallpaper vem do slider do Menu de aplicativo (0..320 px);
        // workspace/hotseat/janela seguem com 320 px fixos, como sempre.
        // XAULINXS_POPUPS_V4: com um popup aberto na workspace o wallpaper também borra (mesmo raio da
        // workspace/hotseat); no drawer vale o maior entre o arrasto e o popup.
        applyWallpaperBlur(
            maxOf(currentDepth * DrawerWallpaperBlurPreference.getMaxRadiusPx(launcher), popupRadius)
        )
        applyBlurRadius(maxOf(drawerRadius, popupRadius))
    }

    private fun applyWallpaperBlur(radiusPx: Float) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return
        val radius = radiusPx.toInt()
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

    private fun applyBlurRadius(radiusPx: Float) {
        if (radiusPx == appliedRadius) return
        appliedRadius = radiusPx
        applyBlur(radiusPx)
    }

    private fun applyBlur(radiusPx: Float) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return
        val radius = radiusPx.toInt()

        val window = launcher.window
        if (window != null) {
            try {
                window.attributes = window.attributes.apply { blurBehindRadius = radius }
            } catch (_: Exception) {
            }
        }

        val effect = if (radius > 1) {
            RenderEffect.createBlurEffect(radiusPx, radiusPx, Shader.TileMode.CLAMP)
        } else {
            null
        }
        for (view in launcher.depthBlurTargets) {
            view.setRenderEffect(effect)
        }
    }
}
