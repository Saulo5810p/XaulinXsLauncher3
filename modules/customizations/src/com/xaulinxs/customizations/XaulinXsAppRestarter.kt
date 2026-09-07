/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Feature nova (info.txt): botão "Reiniciar para aplicar alterações" no
 * canto superior da aba principal de configurações.
 *
 * Por que Activity.recreate() (já existente via
 * SettingsActivity.LauncherSettingsFragment.tryRecreateActivity) NÃO é
 * suficiente aqui: várias customizações do XaulinXs dependem de estado
 * carregado uma única vez no PROCESSO (Application), não só na Activity
 * de Configurações — por exemplo, o Factory2 de fonte global instalado em
 * attachBaseContext de Launcher/SettingsActivity, o cache de bitmap de
 * ícones em BaseIconFactory (que decide na hora de gerar o bitmap se
 * remove ou não o fundo — bitmaps já gerados e cacheados não são
 * regenerados só por recriar uma Activity), e o wallpaper próprio
 * carregado por XaulinXsInAppWallpaper. recrear só a SettingsActivity não
 * reprocessa nada disso; é preciso matar e reabrir o processo inteiro.
 *
 * Abordagem padrão do Android para "reiniciar o app" (não existe API
 * pública de restart direto): agenda um PendingIntent que reabre a
 * Activity de entrada do launcher (mesma que o sistema usa para abrir o
 * home) via AlarmManager.set(), com um pequeno atraso, e então mata o
 * processo atual com Process.killProcess — o sistema recria o processo do
 * zero (nova instância de Application, novos Factory2, cache de ícones
 * limpo) quando o PendingIntent disparar.
 */
package com.xaulinxs.customizations

import android.app.Activity
import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Process
import android.os.SystemClock

object XaulinXsAppRestarter {

    private const val RESTART_DELAY_MILLIS = 300L

    @JvmStatic
    fun restart(activity: Activity) {
        val context = activity.applicationContext

        // Intent de reabertura: a própria launcher activity do app
        // (com.android.launcher3.Launcher), como uma abertura normal de
        // app — não usa Intent.ACTION_MAIN/CATEGORY_HOME para evitar
        // depender deste app já estar selecionado como launcher padrão
        // no momento do restart.
        val restartIntent = Intent(context, com.android.launcher3.Launcher::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }

        val pendingIntent = PendingIntent.getActivity(
            context,
            0,
            restartIntent,
            PendingIntent.FLAG_CANCEL_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        alarmManager.set(
            AlarmManager.ELAPSED_REALTIME,
            SystemClock.elapsedRealtime() + RESTART_DELAY_MILLIS,
            pendingIntent,
        )

        // Encerra o processo atual — o AlarmManager já agendado acima
        // garante a reabertura; não há "continuação" possível depois
        // desta chamada.
        Process.killProcess(Process.myPid())
    }
}
