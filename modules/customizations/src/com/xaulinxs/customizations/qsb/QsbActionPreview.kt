/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Gera o texto e o ícone do "Predictive Action Badge" — o feedback
 * visual que aparece abaixo do campo do Modo Texto conforme o usuário
 * digita, mostrando qual ação vai ser executada ANTES de apertar
 * Enter. Roda a cada tecla digitada (TextWatcher em OseWidgetView),
 * então precisa ser rápido e nunca bloquear a UI thread com I/O
 * pesado (por isso não resolve contato de verdade aqui — resolução
 * real de contato só acontece na hora de executar/QsbActionExecutor,
 * é I/O contra ContentResolver).
 *
 * Resolução de APP é feita aqui contra o AllAppsStore (já em memória,
 * sem I/O de disco/rede) para o badge poder mostrar o nome real do
 * app encontrado ("Abrir o aplicativo Spotify"), não só o texto cru
 * que o usuário digitou.
 */
package com.xaulinxs.customizations.qsb

import com.android.launcher3.allapps.AllAppsStore

enum class QsbBadgeIcon {
    NONE, OPEN_APP, CALL, WHATSAPP_CALL, MESSAGE, SEARCH,
}

data class QsbActionPreview(val icon: QsbBadgeIcon, val message: String)

object QsbActionPreviewBuilder {

    /**
     * [rawInput] é o texto exatamente como está no campo agora.
     * Retorna null quando não há nada pra mostrar (campo vazio ou
     * nenhum comando reconhecido) — chamador esconde o badge nesse
     * caso.
     */
    @JvmStatic
    fun build(appsStore: AllAppsStore, rawInput: String): QsbActionPreview? {
        if (rawInput.isBlank()) return null
        val action = QsbIntentParser.parse(rawInput)

        return when (action) {
            is QsbAction.Unrecognized -> null

            is QsbAction.OpenApp -> {
                val app = findAppByQuery(appsStore, action.appQuery)
                val label = app?.title?.toString() ?: action.appQuery
                QsbActionPreview(QsbBadgeIcon.OPEN_APP, "Abrir o aplicativo $label")
            }

            is QsbAction.SearchInApp -> {
                val app = findAppByQuery(appsStore, action.appQuery)
                val label = app?.title?.toString() ?: action.appQuery
                QsbActionPreview(QsbBadgeIcon.SEARCH, "Buscar \"${action.query}\" em $label")
            }

            is QsbAction.CallNumber ->
                QsbActionPreview(QsbBadgeIcon.CALL, "Ligar para ${action.number}")

            is QsbAction.CallContact ->
                QsbActionPreview(QsbBadgeIcon.CALL, "Ligar para ${action.contactQuery}")

            is QsbAction.WhatsAppCallNumber ->
                QsbActionPreview(QsbBadgeIcon.WHATSAPP_CALL, "Abrir conversa com ${action.number} no WhatsApp para ligar")

            is QsbAction.WhatsAppCallContact ->
                QsbActionPreview(QsbBadgeIcon.WHATSAPP_CALL, "Abrir conversa com ${action.contactQuery} no WhatsApp para ligar")

            is QsbAction.WhatsAppNumber ->
                QsbActionPreview(QsbBadgeIcon.MESSAGE, whatsAppMessagePreview(action.number, action.message))

            is QsbAction.WhatsAppContact ->
                QsbActionPreview(QsbBadgeIcon.MESSAGE, whatsAppMessagePreview(action.contactQuery, action.message))

            is QsbAction.SmsNumber ->
                QsbActionPreview(QsbBadgeIcon.MESSAGE, smsPreview(action.number, action.message))

            is QsbAction.SmsContact ->
                QsbActionPreview(QsbBadgeIcon.MESSAGE, smsPreview(action.contactQuery, action.message))
        }
    }

    private fun whatsAppMessagePreview(recipient: String, message: String): String =
        if (message.isBlank()) {
            "Abrir conversa com $recipient no WhatsApp"
        } else {
            "Enviar no WhatsApp para $recipient: \"$message\""
        }

    private fun smsPreview(recipient: String, message: String): String =
        if (message.isBlank()) {
            "Abrir SMS para $recipient"
        } else {
            "Enviar SMS para $recipient: \"$message\""
        }

    /** Mesma tolerância de match usada na execução real, sem I/O. */
    private fun findAppByQuery(appsStore: AllAppsStore, query: String) =
        (appsStore.apps ?: emptyArray()).let { apps ->
            val queryLower = query.trim().lowercase()
            apps.firstOrNull { it.title?.toString()?.lowercase() == queryLower }
                ?: apps.firstOrNull { it.title?.toString()?.lowercase()?.startsWith(queryLower) == true }
                ?: apps.firstOrNull { it.title?.toString()?.lowercase()?.contains(queryLower) == true }
        }
}
