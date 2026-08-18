/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * "QSB Super Inteligente" — parser de linguagem natural do Modo Texto.
 *
 * Decisão de arquitetura (substitui a ideia original de usar a lib
 * nativa do LatinIME, libjni_latinime.so): aquela lib é o motor de
 * autocorreção/previsão de teclado do AOSP (BinaryDictionary +
 * ProximityInfo + DicTraverseSession — sugestão por n-gramas e
 * distância de edição). Ela não tem, e não foi desenhada para ter,
 * nenhum conceito de "ação" ou "intenção" — só sabe dizer qual palavra
 * do dicionário é estatisticamente mais provável a partir de outra ou
 * de um toque impreciso. Linkar JNI nela para reconhecer comandos
 * seria trabalho extra (bridge JNI, empacotar arquivo de dicionário
 * .dict, gerenciar ProximityInfo do layout) sem ganho nenhum sobre um
 * parser de regras leve — na real, pioraria: a lib tentaria
 * "corrigir"/prever palavras dentro do comando, e não extrair a ação.
 *
 * Este parser resolve o que o usuário pediu de fato — frase em
 * linguagem natural -> ação estruturada (QsbAction) -> Intent — com
 * reconhecimento de verbo + entidade via regex, 100% on-device, sem
 * dependência nativa nova. Fica aberto para, no futuro, ganhar
 * tolerância a erro de digitação via TextServicesManager/
 * SpellCheckerSession (serviço de correção ortográfica do próprio
 * Android), sem precisar reimplementar o LatinIME dentro do launcher.
 *
 * Cobertura desta primeira versão (ordem de tentativa = ordem de
 * prioridade, primeiro match vence):
 *   1) WhatsApp para contato/número, com mensagem
 *   2) SMS para contato/número, com mensagem
 *   3) Ligar para contato/número
 *   4) Abrir <app> e pesquisar <algo> dentro dele
 *   5) Abrir <app>
 * Qualquer texto que não bata com nenhum padrão -> QsbAction.Unrecognized.
 *
 * Requisito do usuário respeitado: nenhum destes ramos cai para
 * browser/app genérico como fallback — cada um resolve uma ação
 * concreta, e a decisão de fallback só acontece em Unrecognized,
 * fora deste arquivo (OseWidgetView).
 */
package com.xaulinxs.customizations.qsb

object QsbIntentParser {

    // Verbos aceitos por categoria, todos minúsculos (comparação é
    // sempre contra o texto já lowercased). Mantidos como listas
    // simples e não regex "|" gigante para ficar fácil de estender
    // sem risco de quebrar grupos de captura.
    private val OPEN_VERBS = listOf("abrir", "abre", "abrir o", "abre o", "abrir a", "abre a", "open")
    private val CALL_VERBS =
        listOf(
            "ligar para", "ligue para", "liga para", "liga pro", "ligar pro",
            "chamar", "chama",
            "faz ligação para", "faz ligação pro", "fazer ligação para", "fazer ligação pro",
            "faz uma ligação para", "faz uma ligação pro",
            "disca para", "disca pro", "discar para", "discar pro",
        )
    private val WHATSAPP_TRIGGERS =
        listOf("whatsapp", "whats app", "zap", "zapzap")
    private val SMS_TRIGGERS = listOf("sms", "mensagem de texto")
    private val SEARCH_VERBS = listOf("pesquisar", "pesquisa", "procurar", "procura", "buscar", "busca")

    // Aceita "pro", "para o", "pra", "para", "com" antes do destinatário —
    // cobre as variações mais comuns de fala/escrita informal em pt-BR.
    private val RECIPIENT_CONNECTORS = listOf(" pro ", " para o ", " pra ", " para ", " com ")

    // "dizendo", "falando", "escrito", ou dois pontos — separam
    // destinatário do corpo da mensagem em comandos de WhatsApp/SMS.
    private val MESSAGE_CONNECTORS = listOf(" dizendo ", " falando ", " escrito ", " escrevendo ", ": ")

    // Só dígitos, espaços, parênteses, hífen e '+' — o suficiente para
    // reconhecer um número discado diretamente no texto (não valida
    // DDD/formato, só decide "isso parece um número" vs "isso é um nome").
    private val NUMBER_REGEX = Regex("^[+\\d][\\d\\s()-]{6,}$")

    /**
     * Ponto de entrada único do parser. [rawInput] é o texto exatamente
     * como o usuário digitou no campo do Modo Texto, sem normalização
     * prévia feita pelo chamador.
     */
    @JvmStatic
    fun parse(rawInput: String): QsbAction {
        val trimmed = rawInput.trim()
        if (trimmed.isEmpty()) return QsbAction.Unrecognized
        val lower = trimmed.lowercase()

        parseWhatsApp(trimmed, lower)?.let { return it }
        parseSms(trimmed, lower)?.let { return it }
        parseCall(trimmed, lower)?.let { return it }
        parseSearchInApp(trimmed, lower)?.let { return it }
        parseOpenApp(trimmed, lower)?.let { return it }

        return QsbAction.Unrecognized
    }

    // ------------------------------------------------------------------
    // WhatsApp: "manda mensagem no whatsapp pro <alguem> dizendo <texto>"
    // Ordem de busca dos gatilhos é flexível de propósito: o usuário pode
    // falar "whatsapp" antes ou depois do destinatário ("manda whatsapp
    // pra Ana dizendo oi" ou "manda pra Ana no whatsapp dizendo oi").
    // ------------------------------------------------------------------
    private fun parseWhatsApp(original: String, lower: String): QsbAction? {
        if (WHATSAPP_TRIGGERS.none { lower.contains(it) }) return null

        val (recipientRaw, messageRaw) = splitRecipientAndMessage(original, lower) ?: return null
        // Remove os próprios gatilhos de "whatsapp" do texto do
        // destinatário, caso tenham ficado colados (ex.: "no whatsapp").
        val recipient = stripTriggerWords(recipientRaw, WHATSAPP_TRIGGERS)
        if (recipient.isBlank()) return null

        return if (looksLikeNumber(recipient)) {
            QsbAction.WhatsAppNumber(normalizeNumber(recipient), messageRaw)
        } else {
            QsbAction.WhatsAppContact(recipient, messageRaw)
        }
    }

    // ------------------------------------------------------------------
    // SMS: mesmo formato do WhatsApp, gatilho "sms" / "mensagem de texto"
    // em vez de "whatsapp". Verificado depois do WhatsApp de propósito —
    // "manda mensagem" sozinho (sem "sms" nem "whatsapp") não deve cair
    // aqui, só quando o gatilho SMS aparece explicitamente.
    // ------------------------------------------------------------------
    private fun parseSms(original: String, lower: String): QsbAction? {
        if (SMS_TRIGGERS.none { lower.contains(it) }) return null

        val (recipientRaw, messageRaw) = splitRecipientAndMessage(original, lower) ?: return null
        val recipient = stripTriggerWords(recipientRaw, SMS_TRIGGERS)
        if (recipient.isBlank()) return null

        return if (looksLikeNumber(recipient)) {
            QsbAction.SmsNumber(normalizeNumber(recipient), messageRaw)
        } else {
            QsbAction.SmsContact(recipient, messageRaw)
        }
    }

    /**
     * Extrai destinatário e corpo da mensagem de um comando do tipo
     * "<verbo> mensagem [no <canal>] pro <destinatário> dizendo <corpo>".
     * O corpo é opcional: se não houver conector de mensagem, o
     * destinatário é o resto do texto e o corpo fica vazio (o app
     * de destino abre com o campo de mensagem em branco, pronto pra
     * o usuário digitar).
     */
    private fun splitRecipientAndMessage(original: String, lower: String): Pair<String, String>? {
        val connectorIndex =
            RECIPIENT_CONNECTORS
                .map { connector -> connector to lower.indexOf(connector) }
                .filter { (_, index) -> index >= 0 }
                .minByOrNull { (_, index) -> index }
                ?: return null
        val (connector, index) = connectorIndex

        val afterConnector = original.substring(index + connector.length)
        val afterConnectorLower = lower.substring(index + connector.length)

        val messageConnectorIndex =
            MESSAGE_CONNECTORS
                .map { connector2 -> connector2 to afterConnectorLower.indexOf(connector2) }
                .filter { (_, idx) -> idx >= 0 }
                .minByOrNull { (_, idx) -> idx }

        return if (messageConnectorIndex != null) {
            val (msgConnector, msgIndex) = messageConnectorIndex
            val recipient = afterConnector.substring(0, msgIndex).trim()
            val message = afterConnector.substring(msgIndex + msgConnector.length).trim()
            recipient to message
        } else {
            afterConnector.trim() to ""
        }
    }

    // ------------------------------------------------------------------
    // Ligação: "ligar para <contato ou número>"
    // ------------------------------------------------------------------
    private fun parseCall(original: String, lower: String): QsbAction? {
        val verb = CALL_VERBS.firstOrNull { lower.startsWith(it + " ") } ?: return null
        val target = original.substring(verb.length).trim()
        if (target.isBlank()) return null

        return if (looksLikeNumber(target)) {
            QsbAction.CallNumber(normalizeNumber(target))
        } else {
            QsbAction.CallContact(target)
        }
    }

    // ------------------------------------------------------------------
    // Pesquisa dentro de app: "abrir <app> e pesquisar <algo>"
    // Checado ANTES de parseOpenApp: sem essa ordem, "abrir chrome e
    // pesquisar gatos" seria capturado por parseOpenApp com appQuery
    // = "chrome e pesquisar gatos" (nome de app inválido, sem resolver
    // a pesquisa em si).
    // ------------------------------------------------------------------
    private fun parseSearchInApp(original: String, lower: String): QsbAction? {
        val openVerb = OPEN_VERBS.firstOrNull { lower.startsWith(it + " ") } ?: return null
        val afterOpen = original.substring(openVerb.length).trim()
        val afterOpenLower = afterOpen.lowercase()

        val searchVerb = SEARCH_VERBS.firstOrNull { verb -> " $afterOpenLower ".contains(" $verb ") }
            ?: return null
        val searchIndex = afterOpenLower.indexOf(searchVerb)
        if (searchIndex <= 0) return null

        // Remove conectores soltos ("e", "e depois") entre o nome do
        // app e o verbo de busca, sem exigir uma lista fixa de todas
        // as combinações — corta na última ocorrência de " e " antes
        // do verbo de busca, se existir.
        var appPart = afterOpen.substring(0, searchIndex).trim()
        val andIndex = appPart.lowercase().lastIndexOf(" e ")
        appPart =
            if (andIndex >= 0) {
                appPart.substring(0, andIndex).trim()
            } else {
                // " e" pode ter ficado colado no fim (sem espaço depois)
                // quando o corte caiu bem em cima do verbo de busca —
                // rfind(" e ") com espaço nos dois lados não bate nesse
                // caso, então trata separado.
                appPart.removeSuffix(" e").trim()
            }
        // Descarta artigos/possessivos soltos que sobraram antes do
        // nome de app de verdade (ex.: "meu navegador Chrome" ->
        // "Chrome"). Nome de app na fala coloquial é tipicamente a
        // última palavra dessa parte do texto.
        appPart = appPart.substringAfterLast(' ').trim()

        var query = afterOpen.substring(searchIndex + searchVerb.length).trim()
        // Remove preposição solta logo após o verbo de busca
        // ("pesquisa POR gatos", "pesquisa SOBRE gatos") — sem isso a
        // query levaria a preposição junto.
        for (prep in listOf("por ", "sobre ", "de ")) {
            if (query.lowercase().startsWith(prep)) {
                query = query.substring(prep.length).trim()
                break
            }
        }
        if (appPart.isBlank() || query.isBlank()) return null

        return QsbAction.SearchInApp(appPart, query)
    }

    // ------------------------------------------------------------------
    // Abrir app: "abrir <app>" — mesmo comportamento (e resolução via
    // AllAppsStore) que o QsbTextModeCommand original já tinha; o
    // parser aqui só reconhece o padrão e devolve a query de app, quem
    // resolve contra a lista de apps instalados continua sendo o
    // chamador (evita este arquivo depender de AllAppsStore).
    // ------------------------------------------------------------------
    private fun parseOpenApp(original: String, lower: String): QsbAction? {
        val verb = OPEN_VERBS.firstOrNull { lower.startsWith(it + " ") } ?: return null
        val appQuery = original.substring(verb.length).trim()
        if (appQuery.isBlank()) return null
        return QsbAction.OpenApp(appQuery)
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    private fun looksLikeNumber(text: String): Boolean = NUMBER_REGEX.matches(stripNumberPrefix(text).trim())

    /**
     * Remove um prefixo falado como "número"/"numero" antes do dígito
     * de fato ("liga pro número 11987654321" -> "11987654321") — sem
     * isso, a palavra extra impede o NUMBER_REGEX de bater e o alvo
     * cai incorretamente como nome de contato.
     */
    private fun stripNumberPrefix(text: String): String {
        val trimmed = text.trim()
        for (prefix in listOf("número ", "numero ", "num ")) {
            if (trimmed.lowercase().startsWith(prefix)) return trimmed.substring(prefix.length).trim()
        }
        return trimmed
    }

    private fun normalizeNumber(text: String): String = stripNumberPrefix(text).filter { it.isDigit() || it == '+' }

    private fun stripTriggerWords(text: String, triggers: List<String>): String {
        var result = text
        for (trigger in triggers) {
            result = result.replace(Regex("(?i)\\bno $trigger\\b"), "")
            result = result.replace(Regex("(?i)\\bpelo $trigger\\b"), "")
            result = result.replace(Regex("(?i)\\b$trigger\\b"), "")
        }
        return result.trim().trim(',', '.', ' ')
    }
}
