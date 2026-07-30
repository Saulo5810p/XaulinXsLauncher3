/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Guarda a instância mutável de "window blur state" que o Dagger expõe
 * como com.android.launcher3.util.WindowBlurState. O AOSP no_quickstep
 * original sempre provê esse valor como `false` (sem capacidade de
 * mutação), pois nesse flavor não existe o mecanismo formal de
 * cross-window blur do Quickstep/SystemUiProxy. Como implementamos nosso
 * próprio blur, precisamos poder atualizar esse valor para `true` quando
 * o desfoque está ativo — é o que ActivityAllAppsContainerView usa para
 * decidir entre a cor de fundo translúcida do App Drawer ou um fallback
 * opaco.
 */
package com.xaulinxs.customizations.blur

import com.android.launcher3.util.MutableListenableRef

object XaulinXsWindowBlurStateHolder {
    private val mutableState = MutableListenableRef(false)

    val state = mutableState.asListenable()

    fun setBlurEnabled(enabled: Boolean) {
        mutableState.dispatchValue(enabled)
    }
}
