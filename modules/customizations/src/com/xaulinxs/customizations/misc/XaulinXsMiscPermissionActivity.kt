/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Activity transparente que mostra o popup de permissão de runtime
 * (localização para o clima, áudio para o player). Mesmo motivo da
 * XaulinXsQsbPermissionActivity: Launcher.java não implementa
 * onRequestPermissionsResult e não vamos mexer nisso.
 */
package com.xaulinxs.customizations.misc

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class XaulinXsMiscPermissionActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val perms = intent.getStringArrayExtra(EXTRA_PERMISSIONS)
        if (perms.isNullOrEmpty()) {
            finish()
            return
        }
        ActivityCompat.requestPermissions(this, perms, REQUEST_CODE)
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray,
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        finish()
        XaulinXsMiscPermissions.dispatchChanged()
    }

    companion object {
        private const val REQUEST_CODE = 7301
        private const val EXTRA_PERMISSIONS = "xaulinxs_permissions"

        @JvmStatic
        fun request(context: Context, permissions: Array<String>) {
            val missing = permissions.filter {
                ContextCompat.checkSelfPermission(context, it) != PackageManager.PERMISSION_GRANTED
            }
            if (missing.isEmpty()) return
            context.startActivity(
                Intent(context, XaulinXsMiscPermissionActivity::class.java)
                    .putExtra(EXTRA_PERMISSIONS, missing.toTypedArray())
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
            )
        }
    }
}

/** Permissões usadas pelos widgets + aviso de "mudou" para quem estiver escutando. */
object XaulinXsMiscPermissions {

    @JvmStatic
    val LOCATION = arrayOf(
        android.Manifest.permission.ACCESS_COARSE_LOCATION,
        android.Manifest.permission.ACCESS_FINE_LOCATION,
    )

    @JvmStatic
    val AUDIO: Array<String> =
        if (Build.VERSION.SDK_INT >= 33) arrayOf(android.Manifest.permission.READ_MEDIA_AUDIO)
        else arrayOf(android.Manifest.permission.READ_EXTERNAL_STORAGE)

    private val listeners = java.util.concurrent.CopyOnWriteArrayList<Runnable>()
    private val main = Handler(Looper.getMainLooper())

    fun addListener(r: Runnable) { listeners.addIfAbsent(r) }
    fun removeListener(r: Runnable) { listeners.remove(r) }
    fun dispatchChanged() { main.post { listeners.forEach { it.run() } } }

    @JvmStatic
    fun hasLocation(c: Context) = LOCATION.any {
        ContextCompat.checkSelfPermission(c, it) == PackageManager.PERMISSION_GRANTED
    }

    @JvmStatic
    fun hasAudio(c: Context) = AUDIO.all {
        ContextCompat.checkSelfPermission(c, it) == PackageManager.PERMISSION_GRANTED
    }
}
