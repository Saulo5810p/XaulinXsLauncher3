/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Tilt de inclinação por giroscópio/acelerômetro, portado de
 * SensorTiltUtil.kt do RetroPlayer (rememberDeviceTilt). Lá é Composable
 * com DisposableEffect; aqui é um singleton View System com lifecycle
 * por View.OnAttachStateChangeListener — múltiplas views (Workspace,
 * AllApps) podem se inscrever ao mesmo tempo, o sensor só é registrado
 * enquanto pelo menos uma está anexada à janela, e desregistrado quando
 * a última se desanexa (evita vazar bateria/sensor).
 *
 * Mesma calibração do player: TYPE_ACCELEROMETER, normalizado para
 * ±12°, SENSOR_DELAY_UI. Suavização via SpringAnimation (em vez de
 * animateFloatAsState do Compose) com stiffness equivalente.
 */
package com.xaulinxs.customizations.cinematic

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.view.View
import androidx.dynamicanimation.animation.FloatValueHolder
import androidx.dynamicanimation.animation.SpringAnimation
import androidx.dynamicanimation.animation.SpringForce

object GyroTiltProvider {

    private const val MAX_TILT_DEGREES = 12f
    private const val GRAVITY_MS2 = 9.81f

    @Volatile
    var tiltX: Float = 0f
        private set

    @Volatile
    var tiltY: Float = 0f
        private set

    private var sensorManager: SensorManager? = null
    private var accelerometer: Sensor? = null
    private var listenerRegistered = false
    private val subscribedViews = java.util.Collections.newSetFromMap(
        java.util.WeakHashMap<View, Boolean>()
    )

    private var rawTiltX = 0f
    private var rawTiltY = 0f

    private val springX = SpringAnimation(FloatValueHolder(0f)).apply {
        setSpring(SpringForce(0f).apply { stiffness = 200f; dampingRatio = 0.9f })
        addUpdateListener { _, value, _ -> if (value.isFinite()) tiltX = value }
    }
    private val springY = SpringAnimation(FloatValueHolder(0f)).apply {
        setSpring(SpringForce(0f).apply { stiffness = 200f; dampingRatio = 0.9f })
        addUpdateListener { _, value, _ -> if (value.isFinite()) tiltY = value }
    }

    private val sensorListener = object : SensorEventListener {
        override fun onSensorChanged(event: SensorEvent?) {
            if (event?.sensor?.type != Sensor.TYPE_ACCELEROMETER) return
            val x = event.values[0]
            val y = event.values[1]
            rawTiltX = (x / GRAVITY_MS2 * MAX_TILT_DEGREES).coerceIn(-MAX_TILT_DEGREES, MAX_TILT_DEGREES)
            rawTiltY = (y / GRAVITY_MS2 * MAX_TILT_DEGREES).coerceIn(-MAX_TILT_DEGREES, MAX_TILT_DEGREES)
            springX.spring.finalPosition = rawTiltX
            springY.spring.finalPosition = rawTiltY
            springX.start()
            springY.start()
        }

        override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
    }

    private val attachListener = object : View.OnAttachStateChangeListener {
        override fun onViewAttachedToWindow(v: View) {
            subscribedViews.add(v)
            ensureRegistered(v.context)
        }

        override fun onViewDetachedFromWindow(v: View) {
            subscribedViews.remove(v)
            if (subscribedViews.isEmpty()) unregister()
        }
    }

    /**
     * Inscreve uma View para manter o sensor de giroscópio ativo enquanto
     * ela estiver anexada à janela. Chamar uma vez, tipicamente em
     * onAttachedToWindow/init da View interessada (Workspace, AllApps).
     * Seguro chamar múltiplas vezes para a mesma View.
     *
     * Se o interruptor XaulinXsGyroTiltSetting estiver desativado, a
     * inscrição é ignorada (sensor nunca é registrado, tiltX/tiltY
     * permanecem 0) — ver notifySettingChanged() para o caso do usuário
     * desativar com o sensor já em uso.
     */
    @JvmStatic
    fun subscribe(view: View) {
        view.removeOnAttachStateChangeListener(attachListener)
        view.addOnAttachStateChangeListener(attachListener)
        if (view.isAttachedToWindow) {
            subscribedViews.add(view)
            ensureRegistered(view.context)
        }
    }

    /**
     * Chamar quando o interruptor de configurações mudar em runtime
     * (XaulinXsGyroTiltPreference). Se foi desativado, desregistra o
     * sensor imediatamente mesmo com views ainda anexadas; se foi
     * reativado, tenta re-registrar usando qualquer view já inscrita.
     */
    @JvmStatic
    fun notifySettingChanged(context: Context, enabled: Boolean) {
        if (!enabled) {
            unregister()
            return
        }
        val anyView = subscribedViews.firstOrNull() ?: return
        ensureRegistered(anyView.context)
    }

    private fun ensureRegistered(context: Context) {
        if (listenerRegistered) return
        if (!com.xaulinxs.customizations.cinematic.XaulinXsGyroTiltSetting.isEnabled(context)) return
        val mgr = context.applicationContext
            .getSystemService(Context.SENSOR_SERVICE) as? SensorManager ?: return
        val sensor = mgr.getDefaultSensor(Sensor.TYPE_ACCELEROMETER) ?: return
        sensorManager = mgr
        accelerometer = sensor
        mgr.registerListener(sensorListener, sensor, SensorManager.SENSOR_DELAY_UI)
        listenerRegistered = true
    }

    private fun unregister() {
        sensorManager?.unregisterListener(sensorListener)
        listenerRegistered = false
        tiltX = 0f
        tiltY = 0f
        rawTiltX = 0f
        rawTiltY = 0f
    }
}

// XAULINXS_GYRO_PROVIDER_FILE
// XAULINXS_GYRO_PROVIDER_TOGGLE_SUPPORT
