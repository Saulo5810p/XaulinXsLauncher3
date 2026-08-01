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
import android.view.WindowManager
import android.view.WindowManager.LayoutParams.FLAG_BLUR_BEHIND
import android.view.WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS
import com.android.launcher3.Launcher
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
        if (!isEnabled) {
            applyBlurRadius(0f)
            return
        }
        val drawerRadius = currentDepth * DRAWER_MAX_BLUR_RADIUS_PX
        val popupRadius = if (popupBlurActive) POPUP_BLUR_RADIUS_PX else 0f
        applyBlurRadius(maxOf(drawerRadius, popupRadius))
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
