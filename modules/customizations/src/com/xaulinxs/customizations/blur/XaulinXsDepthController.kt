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
import android.view.WindowManager.LayoutParams.FLAG_BLUR_BEHIND
import com.android.launcher3.Launcher
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.settings.ThemedScrimPreference.Companion.THEMED_SCRIM_ENABLED

private const val MAX_BLUR_RADIUS_PX = 150

class XaulinXsDepthController(private val launcher: Launcher) {

    private var currentDepth = 0f

    private val isEnabled: Boolean
        get() = LauncherPrefs.get(launcher).get(THEMED_SCRIM_ENABLED)

    fun setupWindowBlurFlags() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            launcher.window.addFlags(FLAG_BLUR_BEHIND)
        }
    }

    fun setDepth(depth: Float) {
        val clamped = depth.coerceIn(0f, 1f)
        val target = if (isEnabled) clamped else 0f
        if (target == currentDepth) return
        currentDepth = target
        applyBlur(target)
    }

    private fun applyBlur(depth: Float) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return
        val radius = (depth * MAX_BLUR_RADIUS_PX).toInt()

        try {
            launcher.window.attributes =
                launcher.window.attributes.apply { blurBehindRadius = radius }
        } catch (_: Exception) {
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
