/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * "QSB Super Inteligente" v2 — motor de intenção por PRESENÇA DE
 * PALAVRAS-CHAVE, não por prefixo rígido de frase.
 *
 * Por que a v1 (prefixo rígido, "a frase tem que começar com o verbo
 * exato") não bastava: o usuário quer reconhecimento pelo SENTIDO —
 * se o texto contém "ligar" + o nome de um contato, é uma ligação,
 * não importa a ordem ou as palavras ao redor. Se contém "whatsapp" +
 * "ligar"/"chamar", é uma CHAMADA por WhatsApp (voz/vídeo), não uma
 * mensagem de texto — combinação de sinais, não só o primeiro que
 * bater. E não pode ficar restrito a uma lista fixa de apps: "abrir
 * <qualquer coisa> e pesquisar <algo>" tem que funcionar pra
 * QUALQUER app instalado, resolvido dinamicamente contra o
 * AllAppsStore, nunca contra uma lista hardcoded tipo
 * ["youtube","spotify","netflix"].
 *
 * Decisão de arquitetura mantida da v1: nada de libjni_latinime.so —
 * aquela lib é motor de autocorreção/previsão de teclado (n-gramas),
 * sem conceito de ação. Este parser continua sendo regras leves
 * on-device, só que agora por classificação de tokens em vez de regex
 * de frase inteira.
 *
 * Arquitetura do motor:
 *   1) Tokeniza o texto inteiro (minúsculo, sem pontuação nas bordas).
 *   2) Classifica quais CATEGORIAS de sinal estão presentes:
 *      SIGNAL_CALL ("ligar", "chamar", "discar", "telefonar", ...),
 *      SIGNAL_WHATSAPP ("whatsapp", "whats", "zap", "zapzap"),
 *      SIGNAL_MESSAGE ("mensagem", "manda", "envia", "escreve", ...),
 *      SIGNAL_SMS ("sms"),
 *      SIGNAL_OPEN ("abrir", "abre", "open"),
 *      SIGNAL_SEARCH ("pesquisar", "pesquisa", "buscar", "busca",
 *      "procurar", "procura").
 *   3) Combina os sinais presentes para decidir o ActionKind:
 *      WHATSAPP + CALL         -> chamada de voz pelo WhatsApp
 *      WHATSAPP (sem CALL)     -> mensagem de texto pelo WhatsApp
 *      SMS                     -> mensagem de texto por SMS
 *      CALL (sem WHATSAPP)     -> ligação pela discadora nativa
 *      OPEN + SEARCH           -> abrir app + pesquisar dentro dele
 *      OPEN (sem SEARCH)       -> abrir app
 *      nenhum sinal reconhecido-> Unrecognized (cai pro Modo Web)
 *   4) Extrai o ALVO (nome de contato/número, ou nome de app+query)
 *      removendo do texto os tokens de sinal já consumidos — sobra só
 *      o que importa (nome, número, mensagem, termo de busca).
 *
 * Resolução de app continua fora deste arquivo (QsbActionExecutor),
 * contra o AllAppsStore real — nunca uma lista fixa de nomes de app.
 */
package com.xaulinxs.customizations.qsb

object QsbIntentParser {

    private val CALL_SIGNAL_WORDS =
        setOf("ligar", "ligue", "liga", "chamar", "chama", "discar", "disca", "telefonar", "telefona", "call")
    private val WHATSAPP_SIGNAL_WORDS = setOf("whatsapp", "whats", "zap", "zapzap")
    private val SMS_SIGNAL_WORDS = setOf("sms")
    private val MESSAGE_SIGNAL_WORDS =
        setOf("mensagem", "manda", "mandar", "envia", "enviar", "escreve", "escrever", "msg")
    private val OPEN_SIGNAL_WORDS = setOf("abrir", "abre", "abra", "open")
    private val SEARCH_SIGNAL_WORDS = setOf("pesquisar", "pesquisa", "pesquise", "buscar", "busca", "busque", "procurar", "procura", "procure")

    // Palavras de função sem valor semântico próprio: descartadas ao
    // montar o alvo (nome/mensagem/query), senão "para o João" vira
    // alvo "para o João" em vez de só "João".
    private val STOPWORDS =
        setOf(
            "para", "pra", "pro", "o", "a", "os", "as", "um", "uma", "no", "na", "nos", "nas",
            "com", "de", "do", "da", "por", "pelo", "pela", "sobre", "e", "meu", "minha", "meus", "minhas",
            "que", "diz", "dizendo", "falando", "falar", "escrito", "escrevendo",
        )

    // Prefixo "número"/"numero" falado antes de um número discado
    // ("ligar pro número 11987654321") — descartado ao normalizar.
    private val NUMBER_WORD_PREFIXES = setOf("número", "numero", "num")

    private val NUMBER_REGEX = Regex("^[+\\d][\\d\\s()-]{5,}$")

    /**
     * Ponto de entrada único. [rawInput] é o texto exatamente como
     * está no campo agora — chamado a cada tecla digitada (para o
     * badge preditivo) e de novo no Enter (para executar de fato).
     * Determinístico: mesmo texto sempre produz o mesmo QsbAction.
     */
    @JvmStatic
    fun parse(rawInput: String): QsbAction {
        val trimmed = rawInput.trim()
        if (trimmed.isEmpty()) return QsbAction.Unrecognized

        val tokens = tokenize(trimmed)
        if (tokens.isEmpty()) return QsbAction.Unrecognized

        val hasCall = tokens.any { it in CALL_SIGNAL_WORDS }
        val hasWhatsapp = tokens.any { it in WHATSAPP_SIGNAL_WORDS }
        val hasSms = tokens.any { it in SMS_SIGNAL_WORDS }
        val hasMessage = tokens.any { it in MESSAGE_SIGNAL_WORDS }
        val hasOpen = tokens.any { it in OPEN_SIGNAL_WORDS }
        val hasSearch = tokens.any { it in SEARCH_SIGNAL_WORDS }

        // Ordem de decisão = ordem de prioridade quando mais de uma
        // categoria de sinal aparece no mesmo texto.
        return when {
            // WhatsApp + sinal de chamada -> chamada de voz pelo
            // WhatsApp, não mensagem de texto (combinação de sinais,
            // não o primeiro que bateu).
            hasWhatsapp && hasCall -> buildRecipientAction(tokens, ::qsbWhatsAppCall)

            // WhatsApp sem sinal de chamada -> mensagem de texto,
            // mesmo sem a palavra "mensagem"/"manda" explícita (ex.:
            // "whatsapp emily tudo bem" do exemplo do usuário).
            hasWhatsapp -> buildRecipientAction(tokens, ::qsbWhatsAppMessage)

            hasSms -> buildRecipientAction(tokens, ::qsbSms)

            // "mensagem"/"manda"/"envia" sem WhatsApp nem SMS
            // explícitos assume SMS (canal nativo do Android) —
            // continua sendo uma mensagem de texto de verdade, nunca
            // cai pro Modo Web só por faltar o nome do canal.
            hasMessage -> buildRecipientAction(tokens, ::qsbSms)

            hasCall -> buildRecipientAction(tokens, ::qsbCall)

            hasOpen && hasSearch -> buildSearchInAppAction(trimmed, tokens)

            hasOpen -> buildOpenAppAction(tokens)

            // Sem nenhum verbo de ação reconhecido, mas ainda assim
            // pode ser "abrir app" implícito (usuário só digitou o
            // nome do app, sem dizer "abrir") — não é um sinal
            // confiável o suficiente pra badge/execução automática
            // nesta versão, então cai pra Unrecognized -> Modo Web.
            else -> QsbAction.Unrecognized
        }
    }

    private fun qsbWhatsAppCall(recipient: String): QsbAction =
        if (looksLikeNumber(recipient)) {
            QsbAction.WhatsAppCallNumber(normalizeNumber(recipient))
        } else {
            QsbAction.WhatsAppCallContact(recipient)
        }

    private fun qsbWhatsAppMessage(recipient: String, message: String): QsbAction =
        if (looksLikeNumber(recipient)) {
            QsbAction.WhatsAppNumber(normalizeNumber(recipient), message)
        } else {
            QsbAction.WhatsAppContact(recipient, message)
        }

    private fun qsbSms(recipient: String, message: String): QsbAction =
        if (looksLikeNumber(recipient)) {
            QsbAction.SmsNumber(normalizeNumber(recipient), message)
        } else {
            QsbAction.SmsContact(recipient, message)
        }

    private fun qsbCall(recipient: String): QsbAction =
        if (looksLikeNumber(recipient)) {
            QsbAction.CallNumber(normalizeNumber(recipient))
        } else {
            QsbAction.CallContact(recipient)
        }

    /**
     * Monta uma ação "só destinatário" (chamadas), delegando para
     * [build]. Usado quando a ação não carrega corpo de mensagem.
     */
    private inline fun buildRecipientAction(tokens: List<String>, build: (String) -> QsbAction): QsbAction {
        val recipient = extractRecipient(tokens)
        if (recipient.isBlank()) return QsbAction.Unrecognized
        return build(recipient)
    }

    /**
     * Sobrecarga para ações "destinatário + mensagem" (WhatsApp/SMS
     * texto). [build] recebe (destinatário, corpo da mensagem) —
     * corpo pode ser vazio (abre o app já na conversa certa, sem
     * texto pré-preenchido, quando o usuário não escreveu nada além
     * do nome).
     */
    private inline fun buildRecipientAction(
        tokens: List<String>,
        build: (String, String) -> QsbAction,
    ): QsbAction {
        val (recipient, message) = extractRecipientAndMessage(tokens)
        if (recipient.isBlank()) return QsbAction.Unrecognized
        return build(recipient, message)
    }

    /**
     * Extrai o destinatário removendo todos os tokens de sinal
     * conhecidos (ligar/whatsapp/sms/mensagem/abrir/pesquisar) e
     * stopwords — o que sobra é o nome/número. Não tenta separar
     * mensagem aqui (usado só por ações sem corpo de mensagem).
     */
    private fun extractRecipient(tokens: List<String>): String {
        val allSignalWords =
            CALL_SIGNAL_WORDS + WHATSAPP_SIGNAL_WORDS + SMS_SIGNAL_WORDS + MESSAGE_SIGNAL_WORDS +
                OPEN_SIGNAL_WORDS + SEARCH_SIGNAL_WORDS
        return tokens
            .filter { it !in allSignalWords && it !in STOPWORDS }
            .joinToString(" ")
            .trim()
    }

    /**
     * Extrai destinatário + mensagem para ações WhatsApp/SMS. Como o
     * motor agora é por palavra-chave (não posição fixa na frase), a
     * heurística é: se houver um conector explícito de mensagem
     * ("dizendo"/"falando"/":"), tudo antes dele é destinatário e
     * tudo depois é mensagem. Sem conector explícito (ex.: "whatsapp
     * emily tudo bem"), assume o PRIMEIRO token restante como nome do
     * contato e o resto como mensagem — cobre o caso mais comum sem
     * exigir acesso à agenda dentro do parser (que não conhece
     * Android de propósito, pra continuar testável isoladamente).
     * Nomes compostos sem conector explícito ("Ana Paula, oi") ficam
     * fora desta primeira versão; o caminho recomendado nesse caso é
     * usar "dizendo"/"falando" para marcar onde o nome termina.
     */
    private fun extractRecipientAndMessage(tokens: List<String>): Pair<String, String> {
        val allSignalWords =
            CALL_SIGNAL_WORDS + WHATSAPP_SIGNAL_WORDS + SMS_SIGNAL_WORDS + MESSAGE_SIGNAL_WORDS +
                OPEN_SIGNAL_WORDS + SEARCH_SIGNAL_WORDS
        val remaining = tokens.filter { it !in allSignalWords }

        val messageConnectorIndex = remaining.indexOfFirst { it == "dizendo" || it == "falando" || it == ":" }
        if (messageConnectorIndex >= 0) {
            val recipientTokens = remaining.subList(0, messageConnectorIndex).filter { it !in STOPWORDS }
            val messageTokens = remaining.subList(messageConnectorIndex + 1, remaining.size)
            return recipientTokens.joinToString(" ").trim() to messageTokens.joinToString(" ").trim()
        }

        val meaningful = remaining.filter { it !in STOPWORDS }
        if (meaningful.isEmpty()) return "" to ""
        val recipient = meaningful.first()
        val message = meaningful.drop(1).joinToString(" ").trim()
        return recipient to message
    }

    private fun buildOpenAppAction(tokens: List<String>): QsbAction {
        val appQuery = tokens.filter { it !in OPEN_SIGNAL_WORDS && it !in STOPWORDS }.joinToString(" ").trim()
        if (appQuery.isBlank()) return QsbAction.Unrecognized
        return QsbAction.OpenApp(appQuery)
    }

    /**
     * "abrir <app> e pesquisar <query>" — como o app não vem mais de
     * uma lista fixa, a extração aqui é posicional dentro do texto
     * ORIGINAL (preserva capitalização, útil pra query de busca):
     * tudo entre o verbo de abrir e o verbo de busca é candidato a
     * nome de app; tudo depois do verbo de busca é a query. Resolução
     * de qual token exatamente é o app de verdade (contra apps
     * instalados) acontece no executor.
     */
    private fun buildSearchInAppAction(original: String, tokens: List<String>): QsbAction {
        val lower = original.lowercase()
        val openWord = OPEN_SIGNAL_WORDS.firstOrNull { word -> tokens.contains(word) } ?: return QsbAction.Unrecognized
        val searchWord = SEARCH_SIGNAL_WORDS.firstOrNull { word -> tokens.contains(word) } ?: return QsbAction.Unrecognized

        val openIndex = lower.indexOf(openWord)
        if (openIndex < 0) return QsbAction.Unrecognized
        val afterOpen = original.substring(openIndex + openWord.length)
        val afterOpenLower = afterOpen.lowercase()
        val searchMatch = Regex("\\b${Regex.escape(searchWord)}\\b").find(afterOpenLower) ?: return QsbAction.Unrecognized
        val searchIndexInRemainder = searchMatch.range.first

        var appPart = afterOpen.substring(0, searchIndexInRemainder).trim()
        // Remove conector "e" solto entre o app e o verbo de busca
        // ("Chrome e" -> "Chrome"), com ou sem espaço remanescente.
        if (appPart.lowercase().endsWith(" e")) appPart = appPart.dropLast(2).trim()
        val andIndex = appPart.lowercase().lastIndexOf(" e ")
        if (andIndex >= 0) appPart = appPart.substring(0, andIndex).trim()
        // Descarta artigos/possessivos soltos antes do nome de app de
        // verdade (ex.: "meu navegador Chrome" -> "Chrome") — nome de
        // app na fala coloquial é tipicamente a última palavra.
        appPart = appPart.substringAfterLast(' ').trim()

        var query = afterOpen.substring(searchIndexInRemainder + searchWord.length).trim()
        for (prep in listOf("por ", "sobre ", "de ")) {
            if (query.lowercase().startsWith(prep)) {
                query = query.substring(prep.length).trim()
                break
            }
        }
        if (appPart.isBlank() || query.isBlank()) return QsbAction.Unrecognized
        return QsbAction.SearchInApp(appPart, query)
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    private fun tokenize(text: String): List<String> =
        text
            .lowercase()
            .split(Regex("\\s+"))
            .map { it.trim(',', '.', '!', '?', ';') }
            .filter { it.isNotEmpty() }

    private fun looksLikeNumber(text: String): Boolean = NUMBER_REGEX.matches(stripNumberPrefix(text).trim())

    private fun stripNumberPrefix(text: String): String {
        val trimmed = text.trim()
        val firstWord = trimmed.substringBefore(' ')
        return if (firstWord.lowercase() in NUMBER_WORD_PREFIXES) {
            trimmed.substringAfter(' ').trim()
        } else {
            trimmed
        }
    }

    private fun normalizeNumber(text: String): String = stripNumberPrefix(text).filter { it.isDigit() || it == '+' }
}
