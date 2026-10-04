/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Clima via Open-Meteo (https://open-meteo.com): gratuito para uso não comercial,
 * sem chave de API, aceita latitude/longitude direto. Uma única requisição traz
 * temperatura, umidade, código do tempo (WMO) e chance de chuva por hora.
 * O nome da cidade vem do Geocoder do próprio aparelho (a Open-Meteo não faz
 * geocodificação reversa). Cache de 30 min.
 */
package com.xaulinxs.customizations.misc.weather

import android.annotation.SuppressLint
import android.content.Context
import android.location.Geocoder
import android.location.Location
import android.location.LocationManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import com.xaulinxs.customizations.misc.XaulinXsMiscPermissions
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

object XaulinXsWeatherRepository {

    private const val CACHE_MS = 30 * 60 * 1000L

    private val io = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())

    private var cached: XaulinXsWeatherData? = null
    private var cachedAt = 0L

    fun refresh(context: Context, force: Boolean, callback: (XaulinXsWeatherState) -> Unit) {
        val app = context.applicationContext
        if (!XaulinXsMiscPermissions.hasLocation(app)) {
            callback(XaulinXsWeatherState.NoLocationPermission); return
        }
        val c = cached
        if (!force && c != null && System.currentTimeMillis() - cachedAt < CACHE_MS) {
            callback(XaulinXsWeatherState.Ready(c)); return
        }
        callback(XaulinXsWeatherState.Loading)
        io.execute {
            val result: XaulinXsWeatherState = try {
                val loc = findLocation(app)
                if (loc == null) XaulinXsWeatherState.NoLocation
                else {
                    val data = fetch(app, loc)
                    cached = data; cachedAt = System.currentTimeMillis()
                    XaulinXsWeatherState.Ready(data)
                }
            } catch (e: Exception) {
                // Falha de rede: mantém o último dado bom, se houver.
                cached?.let { XaulinXsWeatherState.Ready(it) }
                    ?: XaulinXsWeatherState.Error("Sem conexão com o clima")
            }
            main.post { callback(result) }
        }
    }

    // ---- localização ----

    @SuppressLint("MissingPermission")
    private fun findLocation(ctx: Context): Location? {
        val lm = ctx.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val providers = try { lm.getProviders(true) } catch (_: Exception) { emptyList() }
        var best: Location? = null
        for (p in providers) {
            val l = try { lm.getLastKnownLocation(p) } catch (_: Exception) { null } ?: continue
            if (best == null || l.time > best.time) best = l
        }
        if (best != null) return best
        if (Build.VERSION.SDK_INT >= 30) {
            val provider = providers.firstOrNull { it != LocationManager.PASSIVE_PROVIDER } ?: return null
            val latch = CountDownLatch(1)
            var out: Location? = null
            lm.getCurrentLocation(provider, null, io) { out = it; latch.countDown() }
            latch.await(10, TimeUnit.SECONDS)
            return out
        }
        return null
    }

    @Suppress("DEPRECATION")
    private fun cityName(ctx: Context, loc: Location): String {
        if (!Geocoder.isPresent()) return ""
        return try {
            val a = Geocoder(ctx, Locale.getDefault()).getFromLocation(loc.latitude, loc.longitude, 1)
                ?.firstOrNull()
            a?.locality ?: a?.subAdminArea ?: a?.adminArea ?: ""
        } catch (_: Exception) { "" }
    }

    // ---- Open-Meteo ----

    private fun fetch(ctx: Context, loc: Location): XaulinXsWeatherData {
        val url = "https://api.open-meteo.com/v1/forecast" +
            "?latitude=${"%.4f".format(Locale.US, loc.latitude)}" +
            "&longitude=${"%.4f".format(Locale.US, loc.longitude)}" +
            "&current=temperature_2m,relative_humidity_2m,is_day,weather_code" +
            "&hourly=precipitation_probability" +
            "&forecast_days=1&timezone=auto"
        val json = JSONObject(get(url))
        val cur = json.getJSONObject("current")

        // Chance de chuva da hora atual: casa "2026-10-04T14:15" com "2026-10-04T14:00".
        var rain = -1
        try {
            val hourly = json.getJSONObject("hourly")
            val times = hourly.getJSONArray("time")
            val probs = hourly.getJSONArray("precipitation_probability")
            val hourKey = cur.getString("time").take(13)
            for (i in 0 until times.length()) {
                if (times.getString(i).startsWith(hourKey)) {
                    if (!probs.isNull(i)) rain = probs.getInt(i)
                    break
                }
            }
        } catch (_: Exception) {
            // Chance de chuva é opcional.
        }

        val code = cur.optInt("weather_code", 0)
        return XaulinXsWeatherData(
            city = cityName(ctx, loc),
            temperatureC = cur.getDouble("temperature_2m"),
            conditionText = describe(code),
            humidityPercent = cur.optInt("relative_humidity_2m", -1),
            rainChancePercent = rain,
            isDay = cur.optInt("is_day", 1) == 1,
            weatherCode = code,
        )
    }

    private fun get(url: String): String {
        val conn = URL(url).openConnection() as HttpURLConnection
        conn.connectTimeout = 10_000
        conn.readTimeout = 10_000
        try {
            if (conn.responseCode != 200) throw IllegalStateException("Open-Meteo respondeu ${conn.responseCode}")
            return conn.inputStream.bufferedReader().use { it.readText() }
        } finally {
            conn.disconnect()
        }
    }

    /** Códigos WMO usados pelo Open-Meteo. */
    fun describe(code: Int): String = when (code) {
        0 -> "Céu limpo"
        1 -> "Predomínio de sol"
        2 -> "Parcialmente nublado"
        3 -> "Nublado"
        45, 48 -> "Neblina"
        51, 53, 55 -> "Garoa"
        56, 57 -> "Garoa congelante"
        61 -> "Chuva fraca"
        63 -> "Chuva"
        65 -> "Chuva forte"
        66, 67 -> "Chuva congelante"
        71, 73, 75, 77 -> "Neve"
        80, 81 -> "Pancadas de chuva"
        82 -> "Pancadas fortes"
        85, 86 -> "Pancadas de neve"
        95 -> "Trovoada"
        96, 99 -> "Trovoada com granizo"
        else -> "Tempo variável"
    }

    fun isRainy(code: Int) = code in 51..67 || code in 80..82 || code in 95..99
}
