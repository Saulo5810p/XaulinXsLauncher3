/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Porte direto do StoragePermissionHelper do projeto irmão XaulinXs
 * LatinIME (já validado lá). Trata as três eras de permissão de storage:
 *  - Android 11+ (API 30+): MANAGE_EXTERNAL_STORAGE, tela especial do
 *    sistema (não é o diálogo padrão de runtime permission).
 *  - Android 6-10 (API 23-29): READ/WRITE_EXTERNAL_STORAGE via diálogo
 *    padrão de runtime permission.
 *  - Android 5-5.1: concedida na instalação (minSdk deste projeto é 28,
 *    então na prática não se aplica aqui, mas mantido por paridade).
 *
 * Todo o fluxo é defensivo: nenhuma chamada aqui lança exceção não tratada.
 */
package com.xaulinxs.customizations.font

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.Settings
import android.widget.Toast
import android.app.AlertDialog
import androidx.core.content.ContextCompat
import com.android.launcher3.R

internal object XaulinXsStoragePermissionHelper {

    const val REQUEST_CODE_MANAGE_STORAGE = 7002
    const val REQUEST_CODE_LEGACY_STORAGE = 7003

    @JvmStatic
    fun hasStoragePermission(activity: Activity): Boolean {
        return try {
            if (Build.VERSION.SDK_INT >= 30) {
                Environment.isExternalStorageManager()
            } else {
                ContextCompat.checkSelfPermission(
                    activity,
                    android.Manifest.permission.READ_EXTERNAL_STORAGE,
                ) == android.content.pm.PackageManager.PERMISSION_GRANTED
            }
        } catch (e: Exception) {
            false
        }
    }

    /**
     * Mostra um popup explicando por que a permissão é necessária, e só
     * então dispara o fluxo de solicitação do sistema apropriado. Sem esse
     * popup explicativo, o pedido de acesso a "todos os arquivos" tende a
     * ser negado por desconfiança do usuário.
     */
    @JvmStatic
    fun requestStoragePermission(activity: Activity) {
        AlertDialog.Builder(activity)
            .setTitle(R.string.xaulinxs_storage_permission_title)
            .setMessage(R.string.xaulinxs_storage_permission_message)
            .setPositiveButton(R.string.xaulinxs_storage_permission_grant) { _, _ ->
                launchPermissionFlow(activity)
            }
            .setNegativeButton(R.string.xaulinxs_storage_permission_deny, null)
            .setCancelable(true)
            .show()
    }

    private fun launchPermissionFlow(activity: Activity) {
        try {
            if (Build.VERSION.SDK_INT >= 30) {
                val intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                intent.data = Uri.parse("package:" + activity.packageName)
                activity.startActivityForResult(intent, REQUEST_CODE_MANAGE_STORAGE)
            } else {
                androidx.core.app.ActivityCompat.requestPermissions(
                    activity,
                    arrayOf(
                        android.Manifest.permission.READ_EXTERNAL_STORAGE,
                        android.Manifest.permission.WRITE_EXTERNAL_STORAGE,
                    ),
                    REQUEST_CODE_LEGACY_STORAGE,
                )
            }
        } catch (e: Exception) {
            try {
                val fallback = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                fallback.data = Uri.parse("package:" + activity.packageName)
                activity.startActivity(fallback)
            } catch (fallbackFailure: Exception) {
                Toast.makeText(
                    activity,
                    R.string.xaulinxs_storage_permission_error,
                    Toast.LENGTH_LONG,
                ).show()
            }
        }
    }
}
