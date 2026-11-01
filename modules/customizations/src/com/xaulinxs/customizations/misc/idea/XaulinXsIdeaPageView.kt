/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Página fixa "Sua Ideia...": ÚLTIMA página da Workspace (ver
 * Workspace.xaulinXsInsertIdeaPageIfEnabled), ocupando a grade inteira — por
 * isso nada pode ser solto nela, mesmo esquema da página de música.
 *
 * - Ditado: SpeechRecognizer nativo do Android. Botão de microfone inicia, botão
 *   de pausa para. A gravação é contínua: quando o reconhecedor encerra sozinho
 *   (silêncio), uma nova sessão começa até o usuário apertar pausa.
 * - O texto da ideia NUNCA é apagado nem resetado pelo app: é salvo a cada
 *   alteração (XaulinXsIdeaStore) e só muda quando o usuário edita o campo
 *   (teclado) ou dita mais texto (que é ANEXADO ao final).
 * - Sem linhas visíveis. O limite de linhas é calculado pela altura REAL do
 *   retângulo (StaticLayout com o mesmo paint/largura do EditText): digitação,
 *   colagem e ditado não passam do que cabe, então nada sai da área visível.
 * - Digitar no teclado durante a gravação pausa a gravação (evita o ditado
 *   sobrescrever o que foi digitado). Sair da página (rolar para outra, tela
 *   apagar) também para o microfone.
 */
package com.xaulinxs.customizations.misc.idea

import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.text.Editable
import android.text.InputType
import android.text.Layout
import android.text.StaticLayout
import android.text.TextWatcher
import android.view.Gravity
import android.view.ViewGroup
import android.view.ViewTreeObserver
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.widget.EditText
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import com.android.launcher3.LauncherSettings
import com.android.launcher3.model.data.ItemInfo
import com.xaulinxs.customizations.misc.XaulinXsMiscPermissionActivity
import com.xaulinxs.customizations.misc.XaulinXsMiscPermissions
import com.xaulinxs.customizations.misc.XaulinXsMiscSettings
import java.util.Locale

private const val PAGE_TITLE = "Sua Ideia..."
private const val STATUS_IDLE = "Digite ou toque no microfone para falar"
private const val STATUS_LISTENING = "Ouvindo… fale agora"
private const val STATUS_PAUSED = "Gravação pausada"
private const val STATUS_FULL = "Espaço de linhas esgotado — o texto não cabe mais"
private const val STATUS_DENIED = "Permissão do microfone negada"
private const val STATUS_UNAVAILABLE = "Reconhecimento de voz indisponível neste aparelho"
private const val STATUS_NETWORK = "Reconhecimento indisponível (rede/servidor do ditado)"
private const val STATUS_ERROR = "Não foi possível usar o microfone"

private const val MAX_CONSECUTIVE_ERRORS = 3
private const val MATCH = ViewGroup.LayoutParams.MATCH_PARENT
private const val WRAP = ViewGroup.LayoutParams.WRAP_CONTENT

/** Persistência do texto da ideia (arquivo de preferências próprio, nunca limpo pelo app). */
internal object XaulinXsIdeaStore {
    private const val PREFS = "xaulinxs_idea_page"
    private const val KEY_TEXT = "text"

    fun load(context: Context): String =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_TEXT, "").orEmpty()

    fun save(context: Context, text: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY_TEXT, text).apply()
    }
}

class XaulinXsIdeaPageView(context: Context) : LinearLayout(context) {

    private val density = resources.displayMetrics.density
    private val main = Handler(Looper.getMainLooper())

    private val input = EditText(context)
    private val statusView = TextView(context)
    private val micButton = ImageButton(context)
    private val pauseButton = ImageButton(context)

    // Estado do texto
    private var programmatic = false
    private var lastGoodText = ""

    // Estado do ditado
    private var recognizer: SpeechRecognizer? = null
    private var wantListening = false       // usuário pediu gravação (vale até apertar pausa)
    private var sessionActive = false       // há uma sessão do SpeechRecognizer rodando
    private var acceptResults = false       // resultados ainda podem entrar no campo
    private var baseText = ""               // texto do campo no início da sessão atual
    private var consecutiveErrors = 0
    private var pendingStartAfterPermission = false

    private val screenLoc = IntArray(2)

    private val restartRunnable = Runnable {
        if (wantListening && !sessionActive) beginSession()
    }
    private val stopAcceptRunnable = Runnable {
        if (!wantListening) acceptResults = false
    }
    private val permissionListener = Runnable { onPermissionResult() }
    private val scrollListener = ViewTreeObserver.OnScrollChangedListener { onPageMoved() }

    private val recognitionListener = object : RecognitionListener {
        override fun onReadyForSpeech(params: Bundle?) {
            if (wantListening) statusView.text = STATUS_LISTENING
        }

        override fun onBeginningOfSpeech() {}

        override fun onRmsChanged(rmsdB: Float) {}

        override fun onBufferReceived(buffer: ByteArray?) {}

        override fun onEndOfSpeech() {}

        override fun onError(error: Int) {
            sessionActive = false
            handleError(error)
        }

        override fun onResults(results: Bundle?) {
            sessionActive = false
            val best = firstResult(results)
            if (acceptResults && best.isNotBlank()) {
                consecutiveErrors = 0
                applySpeech(best)
            }
            if (wantListening) scheduleRestart(250) else acceptResults = false
        }

        override fun onPartialResults(partialResults: Bundle?) {
            val best = firstResult(partialResults)
            if (acceptResults && best.isNotBlank()) applySpeech(best)
        }

        override fun onEvent(eventType: Int, params: Bundle?) {}
    }

    init {
        orientation = VERTICAL
        super.setPadding(dp(16), dp(16), dp(16), dp(16))

        val title = TextView(context).apply {
            text = PAGE_TITLE
            setTextColor(Color.WHITE)
            textSize = 22f
            setTypeface(typeface, Typeface.BOLD)
            setShadowLayer(dp(3).toFloat(), 0f, dp(1).toFloat(), 0x99000000.toInt())
        }
        addView(title, LayoutParams(MATCH, WRAP).apply { bottomMargin = dp(12) })

        configureInput()
        addView(input, LayoutParams(MATCH, 0, 1f))

        statusView.apply {
            text = STATUS_IDLE
            setTextColor(Color.WHITE)
            textSize = 14f
            gravity = Gravity.CENTER
            setShadowLayer(dp(3).toFloat(), 0f, dp(1).toFloat(), 0x99000000.toInt())
        }
        addView(statusView, LayoutParams(MATCH, WRAP).apply { topMargin = dp(12) })

        val row = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }
        configureRoundButton(micButton, android.R.drawable.ic_btn_speak_now, "Gravar")
        configureRoundButton(pauseButton, android.R.drawable.ic_media_pause, "Pausar")
        val size = dp(64)
        row.addView(micButton, LayoutParams(size, size))
        row.addView(pauseButton, LayoutParams(size, size).apply { marginStart = dp(28) })
        addView(row, LayoutParams(MATCH, WRAP).apply { topMargin = dp(10) })

        micButton.setOnClickListener { startRecording() }
        pauseButton.setOnClickListener { stopRecording(STATUS_PAUSED) }
        refreshButtons()

        // Alguns operadores do Workspace (mapOverItems) fazem cast de getTag() para ItemInfo
        // sem checar null; esta etiqueta "não acionável" evita NPE. Nunca é gravada no banco.
        tag = ItemInfo().apply {
            itemType = LauncherSettings.Favorites.ITEM_TYPE_NON_ACTIONABLE
            container = LauncherSettings.Favorites.CONTAINER_DESKTOP
            screenId = XaulinXsMiscSettings.IDEA_SCREEN_ID
        }
        setOnLongClickListener { true }
    }

    // CellLayout.measureChild() aplica padding de ícone em qualquer filho; ignoramos.
    override fun setPadding(left: Int, top: Int, right: Int, bottom: Int) = Unit

    // ------------------------------------------------------------------
    // Construção da UI
    // ------------------------------------------------------------------

    private fun dp(value: Int): Int = (value * density).toInt()

    private fun configureInput() {
        input.apply {
            hint = PAGE_TITLE
            setHintTextColor(0x99FFFFFF.toInt())
            setTextColor(Color.WHITE)
            textSize = 18f
            gravity = Gravity.TOP or Gravity.START
            inputType = InputType.TYPE_CLASS_TEXT or
                InputType.TYPE_TEXT_FLAG_MULTI_LINE or
                InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
            imeOptions = EditorInfo.IME_FLAG_NO_EXTRACT_UI
            // Quebra determinística: o mesmo critério é usado em measureHeight().
            breakStrategy = Layout.BREAK_STRATEGY_SIMPLE
            hyphenationFrequency = Layout.HYPHENATION_FREQUENCY_NONE
            setHorizontallyScrolling(false)
            isVerticalScrollBarEnabled = false
            overScrollMode = OVER_SCROLL_NEVER
            setPadding(dp(16), dp(14), dp(16), dp(14))
            // Retângulo translúcido com borda branca — sem linhas internas visíveis.
            background = GradientDrawable().apply {
                shape = GradientDrawable.RECTANGLE
                cornerRadius = dp(14).toFloat()
                setColor(0x26000000)
                setStroke(dp(2), 0xCCFFFFFF.toInt())
            }
        }

        val saved = XaulinXsIdeaStore.load(context)
        programmatic = true
        input.setText(saved)
        input.setSelection(saved.length)
        programmatic = false
        lastGoodText = saved

        input.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}

            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}

            override fun afterTextChanged(s: Editable?) {
                onTextEdited(s?.toString().orEmpty())
            }
        })
    }

    private fun configureRoundButton(button: ImageButton, iconRes: Int, description: String) {
        button.apply {
            setImageResource(iconRes)
            setColorFilter(Color.WHITE)
            scaleType = ImageView.ScaleType.CENTER_INSIDE
            contentDescription = description
            setPadding(dp(14), dp(14), dp(14), dp(14))
        }
    }

    private fun applyButtonStyle(button: ImageButton, enabled: Boolean, strokeColor: Int) {
        button.isEnabled = enabled
        button.alpha = if (enabled) 1f else 0.4f
        button.background = GradientDrawable().apply {
            shape = GradientDrawable.OVAL
            setColor(0x26000000)
            setStroke(dp(2), strokeColor)
        }
    }

    private fun refreshButtons() {
        // Microfone fica vermelho enquanto grava.
        applyButtonStyle(
            micButton,
            enabled = !wantListening,
            strokeColor = if (wantListening) 0xFFFF5252.toInt() else 0xCCFFFFFF.toInt(),
        )
        applyButtonStyle(pauseButton, enabled = wantListening, strokeColor = 0xCCFFFFFF.toInt())
    }

    // ------------------------------------------------------------------
    // Ciclo de vida
    // ------------------------------------------------------------------

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        XaulinXsMiscPermissions.addListener(permissionListener)
        viewTreeObserver.addOnScrollChangedListener(scrollListener)
    }

    override fun onDetachedFromWindow() {
        super.onDetachedFromWindow()
        XaulinXsMiscPermissions.removeListener(permissionListener)
        if (viewTreeObserver.isAlive) viewTreeObserver.removeOnScrollChangedListener(scrollListener)
        wantListening = false
        acceptResults = false
        main.removeCallbacks(restartRunnable)
        main.removeCallbacks(stopAcceptRunnable)
        releaseRecognizer()
        XaulinXsIdeaStore.save(context, input.text?.toString().orEmpty())
    }

    override fun onWindowVisibilityChanged(visibility: Int) {
        super.onWindowVisibilityChanged(visibility)
        if (visibility != VISIBLE) {
            stopRecording(STATUS_IDLE)
            hideKeyboard()
        }
    }

    /** Rolou para outra página: para o microfone e fecha o teclado. */
    private fun onPageMoved() {
        if (!wantListening && !input.hasFocus()) return
        getLocationOnScreen(screenLoc)
        val screenWidth = resources.displayMetrics.widthPixels
        val visibleWidth = minOf(screenLoc[0] + width, screenWidth) - maxOf(screenLoc[0], 0)
        if (visibleWidth >= width / 2) return
        if (wantListening) stopRecording(STATUS_IDLE)
        if (input.hasFocus()) {
            input.clearFocus()
            hideKeyboard()
        }
    }

    private fun hideKeyboard() {
        val imm = context.getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager
        imm?.hideSoftInputFromWindow(windowToken, 0)
    }

    private fun toast(message: String) {
        Toast.makeText(context, message, Toast.LENGTH_SHORT).show()
    }

    // ------------------------------------------------------------------
    // Texto: limite de linhas pela altura real do retângulo
    // ------------------------------------------------------------------

    private fun measureHeight(text: CharSequence, widthPx: Int): Int =
        StaticLayout.Builder.obtain(text, 0, text.length, input.paint, widthPx)
            .setAlignment(Layout.Alignment.ALIGN_NORMAL)
            .setLineSpacing(input.lineSpacingExtra, input.lineSpacingMultiplier)
            .setIncludePad(input.includeFontPadding)
            .setBreakStrategy(Layout.BREAK_STRATEGY_SIMPLE)
            .setHyphenationFrequency(Layout.HYPHENATION_FREQUENCY_NONE)
            .build()
            .height

    /** true se [text] cabe inteiro no retângulo sem rolar. Sem layout ainda: não bloqueia. */
    private fun fits(text: CharSequence): Boolean {
        val availableWidth = input.width - input.paddingLeft - input.paddingRight
        val availableHeight = input.height - input.paddingTop - input.paddingBottom - dp(2)
        if (availableWidth <= 0 || availableHeight <= 0) return true
        return measureHeight(text, availableWidth) <= availableHeight
    }

    /** Maior prefixo de [candidate] que cabe, sem cortar abaixo de [minLength] nem no meio de palavra. */
    private fun fitPrefix(candidate: String, minLength: Int): String {
        if (fits(candidate)) return candidate
        var low = minLength.coerceIn(0, candidate.length)
        var high = candidate.length
        while (low < high) {
            val mid = (low + high + 1) / 2
            if (fits(candidate.substring(0, mid))) low = mid else high = mid - 1
        }
        var cut = low
        if (cut > 0 && Character.isHighSurrogate(candidate[cut - 1])) cut--
        // Corta na última fronteira de palavra do trecho novo, se houver.
        if (cut < candidate.length && !candidate[cut].isWhitespace()) {
            val boundary = candidate.substring(0, cut).lastIndexOfAny(charArrayOf(' ', '\n'))
            if (boundary >= minLength) cut = boundary
        }
        return candidate.substring(0, cut).trimEnd(' ')
    }

    private fun setTextProgrammatically(text: String, selection: Int = text.length) {
        programmatic = true
        try {
            input.setText(text)
            input.setSelection(selection.coerceIn(0, input.text.length))
        } finally {
            programmatic = false
        }
        lastGoodText = text
        XaulinXsIdeaStore.save(context, text)
    }

    /** Alteração vinda do usuário (teclado, colar, apagar). */
    private fun onTextEdited(current: String) {
        if (programmatic) return
        if (current.length > lastGoodText.length && !fits(current)) {
            // Passaria do que cabe na área visível: desfaz a entrada.
            val selection = minOf(input.selectionStart.coerceAtLeast(0), lastGoodText.length)
            setTextProgrammatically(lastGoodText, selection)
            statusView.text = STATUS_FULL
            return
        }
        lastGoodText = current
        XaulinXsIdeaStore.save(context, current)
        if (wantListening) {
            // Digitou durante a gravação: pausa para o ditado não sobrescrever o digitado.
            stopRecording(STATUS_PAUSED)
        }
        acceptResults = false
    }

    // ------------------------------------------------------------------
    // Ditado (SpeechRecognizer nativo)
    // ------------------------------------------------------------------

    private fun firstResult(bundle: Bundle?): String =
        bundle?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()

    private fun startRecording() {
        if (wantListening) return
        if (!XaulinXsMiscPermissions.hasMic(context)) {
            pendingStartAfterPermission = true
            XaulinXsMiscPermissionActivity.request(context, XaulinXsMiscPermissions.MIC)
            return
        }
        if (!SpeechRecognizer.isRecognitionAvailable(context)) {
            statusView.text = STATUS_UNAVAILABLE
            toast(STATUS_UNAVAILABLE)
            return
        }
        wantListening = true
        acceptResults = true
        consecutiveErrors = 0
        statusView.text = STATUS_LISTENING
        refreshButtons()
        beginSession()
    }

    private fun beginSession() {
        if (!wantListening) return
        val rec = recognizer ?: SpeechRecognizer.createSpeechRecognizer(context).also {
            it.setRecognitionListener(recognitionListener)
            recognizer = it
        }
        baseText = input.text?.toString().orEmpty()
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(
                RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM,
            )
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault().toLanguageTag())
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, context.packageName)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 3000L)
            putExtra(
                RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS,
                2500L,
            )
        }
        sessionActive = true
        try {
            rec.startListening(intent)
        } catch (e: Exception) {
            sessionActive = false
            stopRecording(STATUS_ERROR)
        }
    }

    private fun scheduleRestart(delayMs: Long) {
        main.removeCallbacks(restartRunnable)
        main.postDelayed(restartRunnable, delayMs)
    }

    private fun stopRecording(status: String) {
        val wasListening = wantListening
        wantListening = false
        pendingStartAfterPermission = false
        main.removeCallbacks(restartRunnable)
        if (wasListening && sessionActive) {
            // stopListening() ainda entrega o último trecho falado em onResults (aceito por ~1,5 s).
            try {
                recognizer?.stopListening()
            } catch (e: Exception) {
                releaseRecognizer()
            }
            main.removeCallbacks(stopAcceptRunnable)
            main.postDelayed(stopAcceptRunnable, 1500L)
        } else {
            acceptResults = false
        }
        refreshButtons()
        statusView.text = status
    }

    private fun releaseRecognizer() {
        sessionActive = false
        try {
            recognizer?.destroy()
        } catch (_: Exception) {
        }
        recognizer = null
    }

    private fun handleError(error: Int) {
        if (!wantListening) {
            acceptResults = false
            return
        }
        when (error) {
            // Silêncio / nada reconhecido: continua ouvindo.
            SpeechRecognizer.ERROR_NO_MATCH,
            SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> scheduleRestart(250)

            SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> stopRecording(STATUS_DENIED)

            SpeechRecognizer.ERROR_NETWORK,
            SpeechRecognizer.ERROR_NETWORK_TIMEOUT,
            SpeechRecognizer.ERROR_SERVER -> stopRecording(STATUS_NETWORK)

            else -> {
                consecutiveErrors++
                if (consecutiveErrors > MAX_CONSECUTIVE_ERRORS) {
                    stopRecording(STATUS_ERROR)
                } else {
                    // BUSY / CLIENT / AUDIO: recria o reconhecedor e tenta de novo.
                    releaseRecognizer()
                    scheduleRestart(600)
                }
            }
        }
    }

    /** Anexa a fala ao texto que já existia no início da sessão (nunca apaga o que estava lá). */
    private fun applySpeech(spoken: String) {
        val piece = spoken.trim()
        if (piece.isEmpty()) return
        val separator = if (baseText.isEmpty() || baseText.last().isWhitespace()) "" else " "
        val candidate = baseText + separator + piece
        val fitted = fitPrefix(candidate, baseText.length)
        setTextProgrammatically(fitted)
        if (fitted.length < candidate.length) {
            // Acabou o espaço visível: para de gravar e avisa.
            stopRecording(STATUS_FULL)
            acceptResults = false
        }
    }

    private fun onPermissionResult() {
        if (!pendingStartAfterPermission) return
        pendingStartAfterPermission = false
        if (XaulinXsMiscPermissions.hasMic(context)) {
            startRecording()
        } else {
            statusView.text = STATUS_DENIED
            toast(STATUS_DENIED)
        }
    }
}
