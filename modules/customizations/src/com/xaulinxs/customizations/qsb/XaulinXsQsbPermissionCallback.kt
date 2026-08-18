/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Ponte estática de curtíssima duração entre XaulinXsQsbPermissionActivity
 * (que efetivamente pede a permissão ao sistema) e o diálogo do Modo
 * Texto na QSB (que precisa reexecutar o comando original assim que a
 * permissão é concedida). Vive só entre "usuário tocou em Conceder" e
 * "resultado do diálogo do sistema voltou" — sempre limpo logo depois
 * de usado, nunca fica pendurado com uma referência antiga.
 */
package com.xaulinxs.customizations.qsb

object XaulinXsQsbPermissionCallback {

    /**
     * Callback de concessão. Setado pela QSB antes de abrir
     * XaulinXsQsbPermissionActivity, chamado por ela quando o usuário
     * concede a permissão, e sempre limpo (null) logo em seguida —
     * tanto em concessão quanto em negação — para nunca reter o
     * [android.content.Context] da View/Activity que o criou além do
     * necessário.
     */
    @Volatile
    var onGranted: ((QsbAction) -> Unit)? = null

    @JvmStatic
    fun consumeIfGranted(action: QsbAction) {
        val callback = onGranted
        onGranted = null
        callback?.invoke(action)
    }

    @JvmStatic
    fun clear() {
        onGranted = null
    }
}
