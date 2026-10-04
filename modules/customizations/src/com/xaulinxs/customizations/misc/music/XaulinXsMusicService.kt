/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Serviço em primeiro plano de reprodução. Usa android.media.MediaPlayer, que
 * toca qualquer formato que o próprio Android suporte (wav, flac, mp3, m4a,
 * opus, ogg, webm, alac em aparelhos com codec...). A notificação é
 * propositalmente simples: só "Reprodução Iniciada!".
 */
package com.xaulinxs.customizations.misc.music

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ServiceInfo
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.media.MediaPlayer
import android.os.Build
import android.os.IBinder
import android.os.PowerManager

class XaulinXsMusicService : Service() {

    private var player: MediaPlayer? = null
    private var prepared = false
    private lateinit var audioManager: AudioManager
    private var focusRequest: AudioFocusRequest? = null

    private val noisyReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == AudioManager.ACTION_AUDIO_BECOMING_NOISY) pausePlayback()
        }
    }

    private val focusListener = AudioManager.OnAudioFocusChangeListener { change ->
        when (change) {
            AudioManager.AUDIOFOCUS_LOSS,
            AudioManager.AUDIOFOCUS_LOSS_TRANSIENT -> pausePlayback()
            AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK -> player?.setVolume(0.3f, 0.3f)
            AudioManager.AUDIOFOCUS_GAIN -> player?.setVolume(1f, 1f)
        }
    }

    override fun onCreate() {
        super.onCreate()
        audioManager = getSystemService(Context.AUDIO_SERVICE) as AudioManager
        XaulinXsPlayer.service = this
        registerReceiver(noisyReceiver, IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY))
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // startForegroundService() exige startForeground() em até 5s, em TODA chamada.
        startAsForeground()
        when (intent?.action) {
            ACTION_PLAY_INDEX -> playIndex(XaulinXsPlayer.index)
            ACTION_TOGGLE -> togglePlayPause()
            ACTION_NEXT -> skipNext(userInitiated = true)
            ACTION_PREV -> skipPrevious()
        }
        return START_NOT_STICKY
    }

    private fun startAsForeground() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.createNotificationChannel(
            NotificationChannel(CHANNEL_ID, "Player de música", NotificationManager.IMPORTANCE_LOW),
        )
        val notification = Notification.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_media_play)
            .setContentTitle("Reprodução Iniciada!")
            .setOngoing(true)
            .build()
        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    // ---- reprodução ----

    private fun playIndex(i: Int) {
        val track = XaulinXsPlayer.queue.getOrNull(i)
        if (track == null) { stopAll(); return }
        XaulinXsPlayer.index = i
        releasePlayer()
        if (!requestFocus()) { setPlaying(false); return }

        val mp = MediaPlayer()
        player = mp
        prepared = false
        try {
            mp.setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                    .build(),
            )
            mp.setWakeMode(applicationContext, PowerManager.PARTIAL_WAKE_LOCK)
            mp.setDataSource(applicationContext, track.uri)
            mp.setOnPreparedListener {
                prepared = true
                it.start()
                setPlaying(true)
            }
            mp.setOnCompletionListener { onTrackCompleted() }
            mp.setOnErrorListener { _, _, _ ->
                // Faixa ilegível (codec não suportado etc.): pula para a próxima em vez de travar.
                skipNext(userInitiated = false)
                true
            }
            mp.prepareAsync()
            XaulinXsPlayer.notifyChanged()
        } catch (e: Exception) {
            skipNext(userInitiated = false)
        }
    }

    private fun onTrackCompleted() {
        if (XaulinXsPlayer.repeatOne) {
            player?.seekTo(0)
            player?.start()
            return
        }
        val last = XaulinXsPlayer.queue.size - 1
        when {
            XaulinXsPlayer.index < last -> playIndex(XaulinXsPlayer.index + 1)
            XaulinXsPlayer.repeatAll -> playIndex(0)
            else -> stopAll()
        }
    }

    private fun skipNext(userInitiated: Boolean) {
        val size = XaulinXsPlayer.queue.size
        if (size == 0) { stopAll(); return }
        val next = XaulinXsPlayer.index + 1
        when {
            next < size -> playIndex(next)
            XaulinXsPlayer.repeatAll || userInitiated -> playIndex(0)
            else -> stopAll()
        }
    }

    private fun skipPrevious() {
        if (positionMs() > 3000) { player?.seekTo(0); return }
        val prev = XaulinXsPlayer.index - 1
        playIndex(if (prev >= 0) prev else (XaulinXsPlayer.queue.size - 1).coerceAtLeast(0))
    }

    private fun togglePlayPause() {
        val mp = player
        if (mp == null || !prepared) { playIndex(XaulinXsPlayer.index.coerceAtLeast(0)); return }
        if (mp.isPlaying) pausePlayback()
        else if (requestFocus()) { mp.start(); setPlaying(true) }
    }

    private fun pausePlayback() {
        player?.takeIf { prepared && it.isPlaying }?.pause()
        setPlaying(false)
    }

    private fun setPlaying(playing: Boolean) {
        XaulinXsPlayer.isPlaying = playing
        XaulinXsPlayer.notifyChanged()
    }

    private fun stopAll() {
        releasePlayer()
        abandonFocus()
        setPlaying(false)
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    fun positionMs(): Int = try {
        if (prepared) player?.currentPosition ?: 0 else 0
    } catch (_: IllegalStateException) { 0 }

    fun seekToMs(ms: Int) {
        val mp = player ?: return
        if (!prepared) return
        try {
            mp.seekTo(ms.coerceIn(0, mp.duration))
        } catch (_: IllegalStateException) {
        }
    }

    private fun releasePlayer() {
        player?.let {
            it.setOnCompletionListener(null)
            it.setOnErrorListener(null)
            it.release()
        }
        player = null
        prepared = false
    }

    private fun requestFocus(): Boolean {
        val req = focusRequest ?: AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                    .build(),
            )
            .setOnAudioFocusChangeListener(focusListener)
            .build().also { focusRequest = it }
        return audioManager.requestAudioFocus(req) == AudioManager.AUDIOFOCUS_REQUEST_GRANTED
    }

    private fun abandonFocus() {
        focusRequest?.let { audioManager.abandonAudioFocusRequest(it) }
    }

    override fun onDestroy() {
        releasePlayer()
        abandonFocus()
        try { unregisterReceiver(noisyReceiver) } catch (_: Exception) {}
        if (XaulinXsPlayer.service === this) XaulinXsPlayer.service = null
        XaulinXsPlayer.isPlaying = false
        XaulinXsPlayer.notifyChanged()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        const val ACTION_PLAY_INDEX = "r.home3.music.PLAY_INDEX"
        const val ACTION_TOGGLE = "r.home3.music.TOGGLE"
        const val ACTION_NEXT = "r.home3.music.NEXT"
        const val ACTION_PREV = "r.home3.music.PREV"
        private const val CHANNEL_ID = "xaulinxs_music"
        private const val NOTIFICATION_ID = 7302
    }
}
