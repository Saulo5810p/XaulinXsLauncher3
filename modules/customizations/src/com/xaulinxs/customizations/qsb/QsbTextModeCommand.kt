/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Ponte entre o campo de texto do Modo Texto da QSB e o motor de
 * "QSB Super Inteligente" (QsbIntentParser + QsbActionExecutor).
 *
 * Fluxo: texto digitado -> QsbIntentParser.parse() (linguagem natural
 * -> QsbAction estruturada) -> QsbActionExecutor.execute() (QsbAction
 * -> Intent real, resolvendo apps/contatos) -> QsbTextModeResult
 * (o que o chamador em OseWidgetView deve fazer: lançar um intent,
 * pedir uma permissão, avisar que não achou o alvo, ou cair no
 * fallback do Modo Web).
 *
 * Nunca cai para Modo Web/browser quando reconhece um comando de
 * verdade — FreeText só acontece quando NADA no texto bate com nenhum
 * padrão conhecido (requisito explícito do usuário).
 */
package com.xaulinxs.customizations.qsb

import android.content.Context
import android.content.Intent
import com.android.launcher3.allapps.AllAppsStore

sealed class QsbTextModeResult {
    /** Intent pronto para disparar. */
    data class Launch(val intent: Intent) : QsbTextModeResult()

    /** Falta permissão de runtime; [retryAction] permite reexecutar após concedida. */
    data class NeedsPermission(val permission: String, val retryAction: QsbAction) :
        QsbTextModeResult()

    /** Comando reconhecido mas alvo (app/contato) não encontrado. */
    data class NotFound(val reason: QsbFailureReason) : QsbTextModeResult()

    /** Nenhum comando reconhecido — chamador decide o fallback (Modo Web). */
    data class FreeText(val text: String) : QsbTextModeResult()
}

object QsbTextModeCommand {

    /**
     * Interpreta [rawInput] contra o dicionário de comandos da QSB
     * Inteligente. [appsStore] resolve nomes de app (mesmo AllAppsStore
     * já carregado em memória pelo launcher, sem PackageManager query
     * nova). [context] é necessário para checar permissão de contatos
     * e resolver Intents de busca contra o PackageManager.
     */
    @JvmStatic
    fun interpret(rawInput: String, appsStore: AllAppsStore, context: Context): QsbTextModeResult {
        val action = QsbIntentParser.parse(rawInput)
        if (action is QsbAction.Unrecognized) {
            return QsbTextModeResult.FreeText(rawInput.trim())
        }

        return when (val outcome = QsbActionExecutor.execute(context, action, appsStore)) {
            is QsbExecutionOutcome.Launch -> QsbTextModeResult.Launch(outcome.intent)
            is QsbExecutionOutcome.NeedsPermission ->
                QsbTextModeResult.NeedsPermission(outcome.permission, outcome.retryAction)
            is QsbExecutionOutcome.ResolutionFailed -> QsbTextModeResult.NotFound(outcome.reason)
            is QsbExecutionOutcome.Unrecognized -> QsbTextModeResult.FreeText(rawInput.trim())
        }
    }

    /**
     * Reexecuta uma [action] já reconhecida anteriormente — usado
     * depois que o usuário concede uma permissão pedida via
     * NeedsPermission, sem precisar digitar o comando de novo.
     */
    @JvmStatic
    fun retry(action: QsbAction, appsStore: AllAppsStore, context: Context): QsbTextModeResult =
        when (val outcome = QsbActionExecutor.execute(context, action, appsStore)) {
            is QsbExecutionOutcome.Launch -> QsbTextModeResult.Launch(outcome.intent)
            is QsbExecutionOutcome.NeedsPermission ->
                QsbTextModeResult.NeedsPermission(outcome.permission, outcome.retryAction)
            is QsbExecutionOutcome.ResolutionFailed -> QsbTextModeResult.NotFound(outcome.reason)
            is QsbExecutionOutcome.Unrecognized -> QsbTextModeResult.FreeText("")
        }
}
