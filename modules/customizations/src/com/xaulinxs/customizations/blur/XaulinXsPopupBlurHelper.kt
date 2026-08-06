/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Ponte entre qualquer ArrowPopup (balão de long-press: menu de contexto de
 * ícone, options popup, etc.) e o XaulinXsDepthController já usado pelo App
 * Drawer. Enquanto o popup está visível, aplicamos o mesmo blur real
 * (RenderEffect) em workspace + hotseat (os depthBlurTargets do AOSP) —
 * ou seja, borramos o que fica ATRÁS do popup, não o popup em si.
 *
 * Chamado a partir de ArrowPopup.java (show() / closeComplete()) via edição
 * cirúrgica — ver comentários "XaulinXs Customizations" lá.
 */
package com.xaulinxs.customizations.blur

import com.android.launcher3.Launcher
import com.android.launcher3.views.ActivityContext

object XaulinXsPopupBlurHelper {

    @JvmStatic
    fun onPopupShown(activityContext: ActivityContext?) {
        val launcher = activityContext as? Launcher ?: return
        if (!com.xaulinxs.customizations.blur.XaulinXsPopupBlur.isEnabled(launcher)) return
        launcher.xaulinXsDepthController?.setPopupBlurActive(true)
    }

    @JvmStatic
    fun onPopupClosed(activityContext: ActivityContext?) {
        (activityContext as? Launcher)?.xaulinXsDepthController?.setPopupBlurActive(false)
    }
}
