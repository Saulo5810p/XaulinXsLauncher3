/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.misc.weather

data class XaulinXsWeatherData(
    /** Pode vir vazio se o aparelho não tiver geocodificador; o widget só omite o nome. */
    val city: String,
    val temperatureC: Double,
    val conditionText: String,
    val humidityPercent: Int,
    /** 0..100, ou -1 se a API não informou. */
    val rainChancePercent: Int,
    val isDay: Boolean,
    /** Código WMO do Open-Meteo (0 = céu limpo ... 99 = trovoada com granizo). */
    val weatherCode: Int,
)

sealed class XaulinXsWeatherState {
    object Loading : XaulinXsWeatherState()
    object NoLocationPermission : XaulinXsWeatherState()
    object NoLocation : XaulinXsWeatherState()
    data class Error(val message: String) : XaulinXsWeatherState()
    data class Ready(val data: XaulinXsWeatherData) : XaulinXsWeatherState()
}
