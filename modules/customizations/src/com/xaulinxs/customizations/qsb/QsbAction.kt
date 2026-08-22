/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Modelo de ação estruturada produzido pelo QsbIntentParser a partir do
 * texto digitado no Modo Texto da QSB. É o "JSON inteligente" da
 * arquitetura pedida pelo usuário: uma representação estruturada e
 * tipada da intenção reconhecida, que o chamador (OseWidgetView)
 * traduz para um Intent real do Android e executa.
 *
 * Fica em memória como sealed class em vez de String JSON serializada
 * de propósito — mesmo conceito (ação estruturada, não texto livre),
 * mas sem overhead de serialização/parsing dentro do mesmo processo.
 * Se algum dia for preciso persistir ou logar a ação (histórico de
 * comandos, por exemplo), dá pra serializar QsbAction para JSON depois
 * sem mudar o parser.
 */
package com.xaulinxs.customizations.qsb

import java.io.Serializable

/**
 * Serializable propositalmente: precisa atravessar um Intent extra ao
 * abrir XaulinXsQsbPermissionActivity (pedido de permissão de
 * contatos em Activity dedicada — ver comentário lá) e voltar depois
 * que o usuário concede/nega, para reexecutar o comando original sem
 * o usuário digitar de novo.
 */
sealed class QsbAction : Serializable {

    /** Abrir um app pelo nome, sem ação específica dentro dele. */
    data class OpenApp(val appQuery: String) : QsbAction()

    /** Ligar para um número discado diretamente no texto. */
    data class CallNumber(val number: String) : QsbAction()

    /** Ligar para um contato salvo, resolvido por nome. */
    data class CallContact(val contactQuery: String) : QsbAction()

    /** Chamada de voz pelo WhatsApp para número discado diretamente (sinal "whatsapp" + "ligar" combinados). */
    data class WhatsAppCallNumber(val number: String) : QsbAction()

    /** Chamada de voz pelo WhatsApp para um contato salvo, resolvido por nome. */
    data class WhatsAppCallContact(val contactQuery: String) : QsbAction()

    /** Mandar mensagem no WhatsApp para um número discado diretamente. */
    data class WhatsAppNumber(val number: String, val message: String) : QsbAction()

    /** Mandar mensagem no WhatsApp para um contato salvo, resolvido por nome. */
    data class WhatsAppContact(val contactQuery: String, val message: String) : QsbAction()

    /** Mandar SMS para um número discado diretamente. */
    data class SmsNumber(val number: String, val message: String) : QsbAction()

    /** Mandar SMS para um contato salvo, resolvido por nome. */
    data class SmsContact(val contactQuery: String, val message: String) : QsbAction()

    /** Abrir um app e, dentro dele, disparar uma pesquisa por [query]. */
    data class SearchInApp(val appQuery: String, val query: String) : QsbAction()

    /** Nenhum comando reconhecido — chamador decide o fallback (Modo Web / texto livre). */
    data object Unrecognized : QsbAction()
}
