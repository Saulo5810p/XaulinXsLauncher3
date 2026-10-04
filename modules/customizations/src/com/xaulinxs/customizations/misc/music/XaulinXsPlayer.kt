/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Estado compartilhado do player. Os dois widgets (lista e mini player) vivem
 * no MESMO processo do serviço de reprodução, então "acompanhar o serviço
 * constantemente" é simplesmente escutar este objeto: o serviço escreve o
 * estado aqui e avisa os listeners; os widgets só leem e mandam comandos.
 * Tudo roda na main thread.
 */
package com.xaulinxs.customizations.misc.music

import android.content.Context
import android.content.Intent
import androidx.core.content.ContextCompat

object XaulinXsPlayer {

    interface Listener { fun onPlayerStateChanged() }

    @JvmStatic var queue: List<XaulinXsAudioTrack> = emptyList()
        internal set
    @JvmStatic var index: Int = -1
        internal set
    @JvmStatic var isPlaying: Boolean = false
        internal set
    @JvmStatic var repeatOne: Boolean = false
        internal set
    @JvmStatic var repeatAll: Boolean = false
        internal set

    internal var service: XaulinXsMusicService? = null

    private val listeners = java.util.concurrent.CopyOnWriteArrayList<Listener>()

    val current: XaulinXsAudioTrack?
        get() = queue.getOrNull(index)

    fun positionMs(): Int = service?.positionMs() ?: 0

    fun addListener(l: Listener) { listeners.addIfAbsent(l) }
    fun removeListener(l: Listener) { listeners.remove(l) }
    internal fun notifyChanged() { listeners.forEach { it.onPlayerStateChanged() } }

    // ---- comandos (viram intents para o serviço em primeiro plano) ----

    fun playQueue(context: Context, tracks: List<XaulinXsAudioTrack>, startIndex: Int) {
        queue = tracks
        index = startIndex
        send(context, XaulinXsMusicService.ACTION_PLAY_INDEX)
    }

    fun togglePlayPause(context: Context) = send(context, XaulinXsMusicService.ACTION_TOGGLE)
    fun next(context: Context) = send(context, XaulinXsMusicService.ACTION_NEXT)
    fun previous(context: Context) = send(context, XaulinXsMusicService.ACTION_PREV)

    /** Seek direto: o serviço roda no mesmo processo, não precisa de intent. */
    fun seekTo(positionMs: Int) {
        service?.seekToMs(positionMs)
    }

    // Repetição é só estado: não precisa acordar o serviço.
    fun toggleRepeatOne() {
        repeatOne = !repeatOne
        if (repeatOne) repeatAll = false
        notifyChanged()
    }

    fun toggleRepeatAll() {
        repeatAll = !repeatAll
        if (repeatAll) repeatOne = false
        notifyChanged()
    }

    private fun send(context: Context, action: String) {
        // Sem faixa carregada, play/next/prev não têm o que fazer.
        if (action != XaulinXsMusicService.ACTION_PLAY_INDEX && queue.isEmpty()) return
        ContextCompat.startForegroundService(
            context.applicationContext,
            Intent(context.applicationContext, XaulinXsMusicService::class.java).setAction(action),
        )
    }
}
