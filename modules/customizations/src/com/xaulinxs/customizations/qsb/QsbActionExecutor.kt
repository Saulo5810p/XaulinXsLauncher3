/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Traduz um QsbAction (saída do QsbIntentParser) em execução real:
 * resolve apps contra o AllAppsStore, resolve contatos contra
 * QsbContactResolver, monta o Intent certo para cada ação, e reporta
 * de volta ao chamador (OseWidgetView) o que fazer — incluindo pedir
 * uma permissão em falta, quando for o caso.
 *
 * Este arquivo não chama startActivity/requestPermissions diretamente:
 * devolve um ExecutionOutcome selado e quem efetivamente dispara a UI
 * é o chamador, que já tem acesso à Activity/View corretos. Mantém a
 * separação: parser não sabe de Android, executor não sabe de UI.
 */
package com.xaulinxs.customizations.qsb

import android.content.Context
import android.content.Intent
import android.net.Uri
import com.android.launcher3.allapps.AllAppsStore
import com.android.launcher3.model.data.AppInfo

sealed class QsbExecutionOutcome {
    /** Intent pronto para ser disparado pelo chamador. */
    data class Launch(val intent: Intent) : QsbExecutionOutcome()

    /** Falta uma permissão de runtime para completar a ação. */
    data class NeedsPermission(val permission: String, val retryAction: QsbAction) :
        QsbExecutionOutcome()

    /** Reconheceu a intenção mas não conseguiu resolver o alvo (app/contato). */
    data class ResolutionFailed(val reason: QsbFailureReason) : QsbExecutionOutcome()

    /** Não reconheceu nenhum comando — chamador decide fallback. */
    data object Unrecognized : QsbExecutionOutcome()
}

enum class QsbFailureReason {
    APP_NOT_FOUND,
    CONTACT_NOT_FOUND,
}

object QsbActionExecutor {


    @JvmStatic
    fun execute(context: Context, action: QsbAction, appsStore: AllAppsStore): QsbExecutionOutcome =
        when (action) {
            is QsbAction.Unrecognized -> QsbExecutionOutcome.Unrecognized

            is QsbAction.OpenApp -> resolveApp(appsStore, action.appQuery)?.let {
                QsbExecutionOutcome.Launch(it.intent)
            } ?: QsbExecutionOutcome.ResolutionFailed(QsbFailureReason.APP_NOT_FOUND)

            is QsbAction.SearchInApp ->
                resolveApp(appsStore, action.appQuery)?.let { app ->
                    QsbExecutionOutcome.Launch(buildSearchIntent(context, app, action.query))
                } ?: QsbExecutionOutcome.ResolutionFailed(QsbFailureReason.APP_NOT_FOUND)

            is QsbAction.CallNumber ->
                QsbExecutionOutcome.Launch(buildCallIntent(action.number))

            is QsbAction.CallContact -> resolveContactOrRequestPermission(context, action, action.contactQuery) { number ->
                buildCallIntent(number)
            }

            // WhatsApp não expõe deep link público/oficial para iniciar
            // uma LIGAÇÃO de voz/vídeo diretamente (só existe API
            // documentada para abrir a conversa) — confirmado: não há
            // um esquema tipo "whatsapp://call?phone=..." suportado.
            // Em vez de fingir automação que não existe (ou depender de
            // ActivityClass não-documentada, que quebra em qualquer
            // atualização do WhatsApp), abre a CONVERSA do contato já
            // pronta — o usuário só precisa tocar no ícone de chamada
            // dentro dela, um toque a mais em vez de zero.
            is QsbAction.WhatsAppCallNumber ->
                QsbExecutionOutcome.Launch(buildWhatsAppIntent(action.number, ""))

            is QsbAction.WhatsAppCallContact -> resolveContactOrRequestPermission(context, action, action.contactQuery) { number ->
                buildWhatsAppIntent(number, "")
            }

            is QsbAction.WhatsAppNumber ->
                QsbExecutionOutcome.Launch(buildWhatsAppIntent(action.number, action.message))

            is QsbAction.WhatsAppContact -> resolveContactOrRequestPermission(context, action, action.contactQuery) { number ->
                buildWhatsAppIntent(number, action.message)
            }

            is QsbAction.SmsNumber ->
                QsbExecutionOutcome.Launch(buildSmsIntent(action.number, action.message))

            is QsbAction.SmsContact -> resolveContactOrRequestPermission(context, action, action.contactQuery) { number ->
                buildSmsIntent(number, action.message)
            }
        }

    /**
     * Compartilhado pelos três tipos de ação "por contato": checa
     * permissão, resolve o nome, e delega a montagem do Intent final
     * para [buildIntent] uma vez que o número é conhecido. Devolve
     * NeedsPermission com a própria [action] original em
     * [QsbExecutionOutcome.NeedsPermission.retryAction] para o
     * chamador poder re-executar exatamente o mesmo comando assim que
     * a permissão for concedida, sem o usuário ter que digitar de novo.
     */
    private inline fun resolveContactOrRequestPermission(
        context: Context,
        action: QsbAction,
        contactQuery: String,
        buildIntent: (phoneNumber: String) -> Intent,
    ): QsbExecutionOutcome {
        if (!QsbContactResolver.hasContactsPermission(context)) {
            return QsbExecutionOutcome.NeedsPermission(android.Manifest.permission.READ_CONTACTS, action)
        }
        val resolved = QsbContactResolver.resolve(context, contactQuery)
            ?: return QsbExecutionOutcome.ResolutionFailed(QsbFailureReason.CONTACT_NOT_FOUND)
        return QsbExecutionOutcome.Launch(buildIntent(resolved.phoneNumber))
    }

    /**
     * Resolução tolerante contra o AllAppsStore real (nunca uma lista
     * fixa de nomes) — cobre nome exato, prefixo, "contém", e por
     * fim "todas as palavras da query aparecem em algum lugar do
     * título do app" (cobre queries como "navegador chrome" batendo
     * em "Google Chrome", mesmo com token extra que não faz parte do
     * nome real do app).
     */
    private fun resolveApp(appsStore: AllAppsStore, query: String): AppInfo? {
        val apps = appsStore.apps ?: emptyArray()
        val queryLower = query.trim().lowercase()
        if (queryLower.isEmpty()) return null

        apps.firstOrNull { it.title?.toString()?.lowercase() == queryLower }?.let { return it }
        apps.firstOrNull { it.title?.toString()?.lowercase()?.startsWith(queryLower) == true }
            ?.let { return it }
        apps.firstOrNull { it.title?.toString()?.lowercase()?.contains(queryLower) == true }
            ?.let { return it }

        val queryWords = queryLower.split(Regex("\\s+")).filter { it.isNotBlank() }
        if (queryWords.size > 1) {
            apps.firstOrNull { app ->
                val title = app.title?.toString()?.lowercase() ?: return@firstOrNull false
                queryWords.any { word -> title.contains(word) }
            }?.let { return it }
        }
        return null
    }

    private fun buildCallIntent(number: String): Intent =
        Intent(Intent.ACTION_CALL, Uri.parse("tel:$number"))

    private fun buildSmsIntent(number: String, message: String): Intent =
        Intent(Intent.ACTION_SENDTO, Uri.parse("smsto:$number")).apply {
            if (message.isNotBlank()) putExtra("sms_body", message)
        }

    /**
     * Usa o esquema de deep link público do WhatsApp (api.whatsapp.com/send)
     * em vez de um Intent de package explícito — funciona tanto com
     * WhatsApp quanto WhatsApp Business (o usuário escolhe se tiver os
     * dois), e não exige declarar consulta de pacote específico no
     * Manifest (Android 11+ visibilidade de pacotes).
     */
    private fun buildWhatsAppIntent(number: String, message: String): Intent {
        val digitsOnly = number.filter { it.isDigit() }
        val uriBuilder = Uri.parse("https://api.whatsapp.com/send").buildUpon()
        uriBuilder.appendQueryParameter("phone", digitsOnly)
        if (message.isNotBlank()) uriBuilder.appendQueryParameter("text", message)
        return Intent(Intent.ACTION_VIEW, uriBuilder.build())
    }

    /**
     * Pesquisa dentro de um app específico. Tenta primeiro
     * ACTION_WEB_SEARCH restrito ao pacote do app (padrão que
     * navegadores e vários apps de busca reconhecem, com o texto em
     * SearchManager.QUERY). Só usa setPackage() se o PackageManager
     * confirmar que o próprio app resolve essa action — sem essa
     * checagem, setPackage() para um app sem esse handler derruba o
     * launcher com ActivityNotFoundException em vez de abrir algo.
     * Sem handler de busca dedicado, cai para abrir o app normalmente
     * (o intent principal dele) — nunca abre um app diferente do
     * pedido, só não consegue pré-preencher a pesquisa.
     */
    private fun buildSearchIntent(context: Context, app: AppInfo, query: String): Intent {
        val packageName = app.componentName?.packageName
        if (packageName != null) {
            val webSearchIntent =
                Intent(Intent.ACTION_WEB_SEARCH).apply {
                    putExtra(android.app.SearchManager.QUERY, query)
                    setPackage(packageName)
                }
            val resolved =
                context.packageManager.resolveActivity(webSearchIntent, android.content.pm.PackageManager.MATCH_DEFAULT_ONLY)
            if (resolved != null) return webSearchIntent
        }
        return app.intent
    }
}
