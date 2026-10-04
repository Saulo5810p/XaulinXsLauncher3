/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Widget 4x2 pequeno: capa, informações da faixa (nome, artista, álbum, pasta,
 * duração), anterior / play-pause / próxima e repetir atual / repetir todas.
 * Acompanha o serviço de reprodução via XaulinXsPlayer (mesmo processo), com
 * um tick de 500 ms só para a barra de progresso enquanto está tocando.
 */
package com.xaulinxs.customizations.misc.music

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.util.Size
import android.util.TypedValue
import android.view.Gravity
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.SeekBar
import android.widget.TextView
import java.util.concurrent.Executors

class XaulinXsMiniPlayerWidget(context: Context) : LinearLayout(context), XaulinXsPlayer.Listener {

    private val cover = ImageView(context)
    private val title = TextView(context)
    private val artist = TextView(context)
    private val albumFolder = TextView(context)
    private val time = TextView(context)
    private val progress = XaulinXsSeekBar(context)
    private var dragging = false
    private val btnPrev = TextView(context)
    private val btnPlay = TextView(context)
    private val btnNext = TextView(context)
    private val btnRepeatOne = TextView(context)
    private val btnRepeatAll = TextView(context)

    private val io = Executors.newSingleThreadExecutor()
    private var shownCoverId = -1L

    private val ticker = object : Runnable {
        override fun run() {
            updateProgress()
            if (XaulinXsPlayer.isPlaying) postDelayed(this, 500)
        }
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    private fun fmt(ms: Long): String {
        val s = ms / 1000
        return "%d:%02d".format(s / 60, s % 60)
    }

    init {
        orientation = HORIZONTAL
        gravity = Gravity.CENTER_VERTICAL
        setPadding(dp(12), dp(10), dp(12), dp(10))
        background = GradientDrawable().apply {
            setColor(Color.argb(170, 20, 20, 24))
            cornerRadius = dp(24).toFloat()
        }

        cover.scaleType = ImageView.ScaleType.CENTER_CROP
        cover.setBackgroundColor(Color.argb(60, 255, 255, 255))
        cover.clipToOutline = true
        cover.outlineProvider = object : android.view.ViewOutlineProvider() {
            override fun getOutline(v: android.view.View, o: android.graphics.Outline) {
                o.setRoundRect(0, 0, v.width, v.height, dp(14).toFloat())
            }
        }
        addView(cover, LayoutParams(dp(96), dp(96)))

        val col = LinearLayout(context).apply { orientation = VERTICAL }
        styleText(title, 15f, true); styleText(artist, 13f, false)
        styleText(albumFolder, 11f, false); styleText(time, 11f, false)
        col.addView(title); col.addView(artist); col.addView(albumFolder)
        progress.max = 1000
        progress.thumbTintList = android.content.res.ColorStateList.valueOf(Color.WHITE)
        progress.progressTintList = android.content.res.ColorStateList.valueOf(Color.WHITE)
        progress.progressBackgroundTintList =
            android.content.res.ColorStateList.valueOf(Color.argb(90, 255, 255, 255))
        progress.setPadding(dp(8), 0, dp(8), 0)
        progress.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(sb: SeekBar, value: Int, fromUser: Boolean) {
                // Enquanto arrasta, só atualiza o tempo mostrado; o seek real é ao soltar.
                val t = XaulinXsPlayer.current ?: return
                if (fromUser) time.text = "${fmt(value * t.durationMs / 1000)} / ${fmt(t.durationMs)}"
            }

            override fun onStartTrackingTouch(sb: SeekBar) {
                dragging = true
            }

            override fun onStopTrackingTouch(sb: SeekBar) {
                dragging = false
                val t = XaulinXsPlayer.current ?: return
                XaulinXsPlayer.seekTo((sb.progress * t.durationMs / 1000).toInt())
            }
        })
        col.addView(progress, LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(28)))
        col.addView(time)

        val controls = LinearLayout(context).apply { gravity = Gravity.CENTER_VERTICAL }
        setupButton(btnRepeatOne, "🔂") { XaulinXsPlayer.toggleRepeatOne() }
        setupButton(btnPrev, "⏮") { XaulinXsPlayer.previous(context) }
        setupButton(btnPlay, "▶") { XaulinXsPlayer.togglePlayPause(context) }
        setupButton(btnNext, "⏭") { XaulinXsPlayer.next(context) }
        setupButton(btnRepeatAll, "🔁") { XaulinXsPlayer.toggleRepeatAll() }
        listOf(btnRepeatOne, btnPrev, btnPlay, btnNext, btnRepeatAll).forEach {
            controls.addView(it, LayoutParams(0, dp(36), 1f))
        }
        col.addView(controls)

        val lp = LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        lp.marginStart = dp(12)
        addView(col, lp)
        render()
    }

    private fun styleText(tv: TextView, sp: Float, bold: Boolean) {
        tv.setTextColor(Color.WHITE); tv.setSingleLine()
        tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, sp)
        tv.ellipsize = android.text.TextUtils.TruncateAt.END
        if (bold) tv.setTypeface(tv.typeface, android.graphics.Typeface.BOLD)
    }

    private fun setupButton(b: TextView, label: String, onClick: () -> Unit) {
        b.text = label
        b.gravity = Gravity.CENTER
        b.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18f)
        b.setTextColor(Color.WHITE)
        b.setOnClickListener { onClick() }
    }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        XaulinXsPlayer.addListener(this)
        render()
    }

    override fun onDetachedFromWindow() {
        XaulinXsPlayer.removeListener(this)
        removeCallbacks(ticker)
        super.onDetachedFromWindow()
    }

    override fun onPlayerStateChanged() = render()

    private fun render() {
        val t = XaulinXsPlayer.current
        if (t == null) {
            title.text = "Nenhuma faixa tocando"
            artist.text = "Escolha uma música na lista"
            albumFolder.text = ""; time.text = ""; progress.progress = 0
            progress.isEnabled = false
            cover.setImageDrawable(null); shownCoverId = -1L
        } else {
            title.text = t.title
            artist.text = t.artist
            albumFolder.text = "${t.album} • ${t.folder}"
            progress.isEnabled = true
            loadCover(t)
            updateProgress()
        }
        btnPlay.text = if (XaulinXsPlayer.isPlaying) "⏸" else "▶"
        btnRepeatOne.alpha = if (XaulinXsPlayer.repeatOne) 1f else 0.4f
        btnRepeatAll.alpha = if (XaulinXsPlayer.repeatAll) 1f else 0.4f
        removeCallbacks(ticker)
        if (XaulinXsPlayer.isPlaying) post(ticker)
    }

    private fun updateProgress() {
        if (dragging) return // não brigar com o dedo do usuário
        val t = XaulinXsPlayer.current ?: return
        val pos = XaulinXsPlayer.positionMs().toLong()
        progress.progress = if (t.durationMs > 0) (pos * 1000 / t.durationMs).toInt() else 0
        time.text = "${fmt(pos)} / ${fmt(t.durationMs)}"
    }

    private fun loadCover(t: XaulinXsAudioTrack) {
        if (shownCoverId == t.id) return
        shownCoverId = t.id
        cover.setImageDrawable(null)
        io.execute {
            val bmp: Bitmap? = try {
                if (Build.VERSION.SDK_INT >= 29) {
                    context.contentResolver.loadThumbnail(t.uri, Size(256, 256), null)
                } else {
                    context.contentResolver
                        .openInputStream(XaulinXsMusicRepository.albumArtUri(t.albumId))
                        ?.use { android.graphics.BitmapFactory.decodeStream(it) }
                }
            } catch (_: Exception) { null }
            post { if (shownCoverId == t.id) cover.setImageBitmap(bmp) }
        }
    }
}
