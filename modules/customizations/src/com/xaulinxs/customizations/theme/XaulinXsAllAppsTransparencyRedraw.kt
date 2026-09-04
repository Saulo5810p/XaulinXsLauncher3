/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * getWorkspaceScrimColor() só é recalculado quando o Launcher entra no
 * estado ALL_APPS (WorkspaceStateTransitionAnimation.setState) — é o
 * mesmo comportamento documentado em ScrimOpacityPreference para
 * SCRIM_OPACITY_PERCENT ("a cor do véu é recalculada do zero toda vez
 * que o App Drawer abre"). Isso já é suficiente para o caso normal: o
 * usuário muda o slider, fecha as configs, abre o menu de apps e vê o
 * valor novo. Este helper cobre só o caso em que o menu de apps já
 * está aberto/em transição enquanto a config muda — força um
 * invalidate() pontual no ScrimView pra refletir na hora.
 */
package com.xaulinxs.customizations.theme

import android.content.Context
import com.android.launcher3.Launcher

object XaulinXsAllAppsTransparencyRedraw {
    @JvmStatic
    fun requestRedraw(context: Context) {
        try {
            val launcher = Launcher.getLauncher(context) ?: return
            // reapplyState() força o StateManager a rodar de novo o setScrim()
            // do estado atual, que é o que efetivamente chama
            // getWorkspaceScrimColor(mLauncher) e empurra a cor recalculada
            // pro ScrimView.
            launcher.stateManager.reapplyState()
            // getBackgroundColor() de ActivityAllAppsContainerView (a camada
            // real que aplica esta transparência, ver
            // applyAllAppsTransparency() em WallpaperScrimHelper.kt) só é
            // repintada dentro de ScrimView.onDraw() via
            // drawOnScrimWithScaleAndBottomOffset — força o invalidate()
            // explicitamente para garantir o redesenho na hora.
            launcher.scrimView?.invalidate()
        } catch (_: Exception) {
            // Contexto pode não ter um Launcher associado (ex.: preference
            // aberta sem o launcher em memória) — sem problema, o valor
            // já foi salvo e será aplicado na próxima vez que o menu de
            // apps abrir de verdade (getWorkspaceScrimColor recalcula do zero).
        }
    }
}

// XAULINXS_ALLAPPS_TRANSPARENCY_REDRAW_FILE
