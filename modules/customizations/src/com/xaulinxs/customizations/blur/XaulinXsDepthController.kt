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

// Raio bem mais agressivo — 150px (~60dp em telas xxhdpi) resultava em um blur
// perceptível como "fraco"; valores de referência do Pixel/One UI passam de
// 100dp de raio efetivo. Em xxhdpi (~2.5x), 320px ≈ 128dp.
private const val MAX_BLUR_RADIUS_PX = 320
private const val TAG = "XaulinXsDepthController"

class XaulinXsDepthController(private val launcher: Launcher) {

    private var currentDepth = 0f

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
        val target = if (isEnabled) clamped else 0f
        XaulinXsWindowBlurStateHolder.setBlurEnabled(
            isEnabled && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S
        )
        if (target == currentDepth) return
        currentDepth = target
        applyBlur(target)
    }

    private fun applyBlur(depth: Float) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return
        val radius = (depth * MAX_BLUR_RADIUS_PX).toInt()

        val window = launcher.window
        if (window != null) {
            try {
                window.attributes = window.attributes.apply { blurBehindRadius = radius }
            } catch (_: Exception) {
            }
        }

        val effect = if (radius > 1) {
            RenderEffect.createBlurEffect(radius.toFloat(), radius.toFloat(), Shader.TileMode.CLAMP)
        } else {
            null
        }
        for (view in launcher.depthBlurTargets) {
            view.setRenderEffect(effect)
        }
    }
}
