/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Parser de comandos do "Modo Texto" da QSB. Sem privilégios de sistema
 * (APK não-system), então o escopo viável é: abrir apps por nome
 * (fuzzy match contra AllAppsStore, já carregado em memória pelo próprio
 * launcher — sem PackageManager query nova) e, quando o texto não bate
 * com nenhum comando reconhecido, cair de volta pro comportamento do
 * Modo Web (busca/browser) — nunca trava o usuário num campo morto.
 *
 * Comandos suportados (prefixo case-insensitive, aceita variações de
 * "abrir"/"abre"/"open"):
 *   "abrir <nome do app>" / "abre <nome do app>" / "open <nome do app>"
 *     -> resolve o app por título (match exato > prefixo > contém) e
 *        dispara o intent principal dele.
 *   qualquer outro texto -> null (chamador decide o fallback: campo de
 *        texto livre ou busca web, conforme QsbConfig.MODE_TEXT_ENABLED
 *        combinado com o texto realmente digitado).
 */
package com.xaulinxs.customizations.qsb

import android.content.Intent
import com.android.launcher3.model.data.AppInfo
import com.android.launcher3.allapps.AllAppsStore

sealed class QsbTextModeResult {
    data class LaunchApp(val appInfo: AppInfo) : QsbTextModeResult()
    data class FreeText(val text: String) : QsbTextModeResult()
}

object QsbTextModeCommand {

    private val OPEN_PREFIXES = listOf("abrir ", "abre ", "open ")

    /**
     * Interpreta [rawInput] contra os apps disponíveis em [appsStore].
     * Retorna LaunchApp se reconhecer um comando de abertura de app com
     * resolução bem-sucedida; caso contrário, FreeText com o texto
     * original (o chamador decide se trata como mensagem livre ou cai
     * para busca web).
     */
    @JvmStatic
    fun interpret(rawInput: String, appsStore: AllAppsStore): QsbTextModeResult {
        val trimmed = rawInput.trim()
        val lower = trimmed.lowercase()

        val prefix = OPEN_PREFIXES.firstOrNull { lower.startsWith(it) }
        if (prefix != null) {
            val appName = trimmed.substring(prefix.length).trim()
            if (appName.isNotEmpty()) {
                resolveApp(appName, appsStore)?.let { return QsbTextModeResult.LaunchApp(it) }
            }
        }

        return QsbTextModeResult.FreeText(trimmed)
    }

    private fun resolveApp(query: String, appsStore: AllAppsStore): AppInfo? {
        // AllAppsStore.getApps() é um platform type Java (AppInfo[], nunca
        // nulo na prática, mas o compilador Kotlin não garante isso) —
        // ?: emptyArray() cobre o caso defensivo sem exigir !! explícito.
        val apps = appsStore.apps ?: emptyArray()
        val queryLower = query.lowercase()

        // Match exato primeiro, depois prefixo, depois "contém" —
        // nessa ordem, pra "abrir play" priorizar "Play Store" com match
        // de prefixo em vez de um app qualquer que só contenha "play"
        // no meio do nome.
        apps.firstOrNull { it.title?.toString()?.lowercase() == queryLower }?.let { return it }
        apps.firstOrNull { it.title?.toString()?.lowercase()?.startsWith(queryLower) == true }
            ?.let { return it }
        apps.firstOrNull { it.title?.toString()?.lowercase()?.contains(queryLower) == true }
            ?.let { return it }
        return null
    }

    @JvmStatic
    fun launchIntentFor(appInfo: AppInfo): Intent = appInfo.intent
}
