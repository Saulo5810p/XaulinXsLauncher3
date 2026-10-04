/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Widget de clima desenhado 100% em Canvas (sem imagens): sol com raios
 * girando, lua, nuvens à deriva e gotículas caindo na proporção da chance de
 * chuva. Textos: temperatura, condição, umidade, chance de chuva e cidade.
 */
package com.xaulinxs.customizations.misc.weather

import android.animation.ValueAnimator
import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.view.View
import android.view.animation.LinearInterpolator
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

class XaulinXsWeatherView(context: Context) : View(context) {

    var state: XaulinXsWeatherState = XaulinXsWeatherState.Loading
        set(value) { field = value; invalidate() }

    private val d = resources.displayMetrics.density
    private val bg = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.argb(150, 20, 28, 48) }
    private val sunPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(255, 196, 40) }
    private val rayPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(255, 214, 90); strokeWidth = 3 * d; strokeCap = Paint.Cap.ROUND
    }
    private val moonPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(235, 238, 250) }
    private val cloudPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.argb(235, 245, 248, 255) }
    private val dropPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(110, 185, 255) }
    private val big = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE; textSize = 34 * d; isFakeBoldText = true
    }
    private val mid = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE; textSize = 14 * d }
    private val small = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(215, 255, 255, 255); textSize = 12 * d
    }

    init {
        isClickable = false
        isFocusable = false
    }

    private var t = 0f // 0..1 em loop
    private val animator = ValueAnimator.ofFloat(0f, 1f).apply {
        duration = 6000
        repeatCount = ValueAnimator.INFINITE
        interpolator = LinearInterpolator()
        addUpdateListener { t = it.animatedValue as Float; invalidate() }
    }

    override fun onAttachedToWindow() { super.onAttachedToWindow(); animator.start() }
    override fun onDetachedFromWindow() { animator.cancel(); super.onDetachedFromWindow() }

    override fun onDraw(canvas: Canvas) {
        val w = width.toFloat(); val h = height.toFloat()
        canvas.drawRoundRect(RectF(0f, 0f, w, h), 24 * d, 24 * d, bg)

        val s = state
        if (s !is XaulinXsWeatherState.Ready) {
            drawIcon(canvas, RectF(12 * d, 12 * d, h - 12 * d, h - 12 * d), sun = true, moon = false, cloud = true, drops = 0)
            val msg = when (s) {
                is XaulinXsWeatherState.Loading -> "Buscando o clima…"
                is XaulinXsWeatherState.NoLocationPermission -> "Permita a localização\n(R's Misc > Widget de clima)"
                is XaulinXsWeatherState.NoLocation -> "Não foi possível obter a localização"
                is XaulinXsWeatherState.Error -> s.message
                else -> ""
            }
            var y = h / 2f - ((msg.count { it == '\n' }) * 9 * d)
            msg.split('\n').forEach { canvas.drawText(it, h, y, mid); y += 18 * d }
            return
        }

        val data = s.data
        val iconBox = RectF(12 * d, 12 * d, h - 12 * d, h - 12 * d)
        val code = data.weatherCode
        val sunny = code in 0..2
        val cloudy = code >= 2
        val raining = XaulinXsWeatherRepository.isRainy(code)
        val drops = when {
            data.rainChancePercent >= 20 -> (data.rainChancePercent / 18).coerceIn(1, 6)
            raining -> 3
            else -> 0
        }
        drawIcon(
            canvas, iconBox,
            sun = data.isDay && sunny, moon = !data.isDay && code in 0..1,
            cloud = cloudy || drops > 0, drops = drops,
        )

        val x = h
        val maxW = w - x - 12 * d
        canvas.drawText("${Math.round(data.temperatureC)}°", x, 12 * d + big.textSize * 0.85f, big)
        canvas.drawText(fit(data.conditionText, mid, maxW - 70 * d), x + 70 * d, 12 * d + 17 * d, mid)
        if (data.city.isNotEmpty()) {
            canvas.drawText(fit(data.city, small, maxW - 70 * d), x + 70 * d, 12 * d + 34 * d, small)
        }

        // linhas de baixo, de baixo para cima: data (subtítulo), chuva, umidade
        val dateY = h - 12 * d
        val rainY = dateY - 17 * d
        val humY = rainY - 17 * d
        val humidity = if (data.humidityPercent >= 0) "Umidade ${data.humidityPercent}%" else "Umidade --"
        canvas.drawText(humidity, x, humY, small)
        val rain = if (data.rainChancePercent >= 0) "Chuva ${data.rainChancePercent}%" else "Chuva --"
        drawDrop(canvas, x + 4 * d, rainY - 5 * d, 5 * d)
        canvas.drawText(rain, x + 14 * d, rainY, small)
        canvas.drawText(todayText(), x, dateY, small)
    }

    /** Dia, mês e ano de hoje no idioma do aparelho, ex.: "4 de outubro de 2026". */
    private fun todayText(): String {
        val locale = java.util.Locale.getDefault()
        val pattern = android.text.format.DateFormat.getBestDateTimePattern(locale, "dMMMMyyyy")
        return java.text.SimpleDateFormat(pattern, locale).format(java.util.Date())
    }

    private fun fit(text: String, p: Paint, maxW: Float): String {
        if (maxW <= 0 || p.measureText(text) <= maxW) return text
        var end = text.length
        while (end > 1 && p.measureText(text, 0, end) + p.measureText("…") > maxW) end--
        return text.substring(0, end) + "…"
    }

    private fun drawIcon(c: Canvas, box: RectF, sun: Boolean, moon: Boolean, cloud: Boolean, drops: Int) {
        val cx = box.centerX(); val cy = box.centerY(); val r = box.width() * 0.5f
        if (sun) {
            val sx = cx - r * 0.15f; val sy = cy - r * 0.2f; val sr = r * 0.32f
            for (i in 0 until 10) {
                val a = (t * 2 * PI + i * 2 * PI / 10).toFloat()
                c.drawLine(sx + cos(a) * sr * 1.35f, sy + sin(a) * sr * 1.35f,
                    sx + cos(a) * sr * 1.75f, sy + sin(a) * sr * 1.75f, rayPaint)
            }
            c.drawCircle(sx, sy, sr, sunPaint)
        }
        if (moon) {
            val mr = r * 0.34f; val mx = cx - r * 0.1f; val my = cy - r * 0.15f
            val p = Path().apply { addCircle(mx, my, mr, Path.Direction.CW) }
            val cut = Path().apply { addCircle(mx + mr * 0.5f, my - mr * 0.2f, mr * 0.9f, Path.Direction.CW) }
            p.op(cut, Path.Op.DIFFERENCE)
            c.drawPath(p, moonPaint)
        }
        if (cloud) {
            val drift = sin(t * 2 * PI).toFloat() * r * 0.06f
            val base = cy + r * 0.12f
            val x0 = cx - r * 0.5f + drift
            c.drawCircle(x0 + r * 0.30f, base, r * 0.24f, cloudPaint)
            c.drawCircle(x0 + r * 0.58f, base - r * 0.16f, r * 0.30f, cloudPaint)
            c.drawCircle(x0 + r * 0.86f, base, r * 0.22f, cloudPaint)
            c.drawRoundRect(RectF(x0 + r * 0.18f, base, x0 + r * 0.98f, base + r * 0.24f), r * 0.12f, r * 0.12f, cloudPaint)
        }
        // gotículas caindo da nuvem; cada uma com fase própria
        for (i in 0 until drops) {
            val phase = (t + i / 6f) % 1f
            val x = cx - r * 0.35f + i * r * 0.14f
            val y = cy + r * 0.38f + phase * r * 0.5f
            dropPaint.alpha = (255 * (1f - phase)).toInt().coerceIn(0, 255)
            drawDrop(c, x, y, r * 0.06f)
        }
        dropPaint.alpha = 255
    }

    private fun drawDrop(c: Canvas, x: Float, y: Float, r: Float) {
        val p = Path().apply {
            moveTo(x, y - r * 1.8f)
            quadTo(x + r * 1.4f, y, x, y + r)
            quadTo(x - r * 1.4f, y, x, y - r * 1.8f)
            close()
        }
        c.drawPath(p, dropPaint)
    }
}
