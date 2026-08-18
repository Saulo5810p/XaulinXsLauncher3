/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Activity transparente (tema ProxyActivityStarterTheme, já usado por
 * outras activities "de passagem" do próprio AOSP neste projeto) cujo
 * único propósito é pedir uma permissão de runtime em nome da QSB
 * Inteligente e devolver o resultado.
 *
 * Existe como Activity dedicada, e não como pedido direto pelo
 * Launcher, porque Launcher.java não implementa
 * onRequestPermissionsResult — adicionar esse override lá mexeria num
 * arquivo grande do AOSP com alto risco de conflito em futuras
 * atualizações do upstream. Isolar em uma Activity nova do pacote
 * XaulinXs Customizations mantém a mudança 100% contida.
 */
package com.xaulinxs.customizations.qsb

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.core.app.ActivityCompat
import androidx.core.content.IntentCompat

class XaulinXsQsbPermissionActivity : Activity() {

    private lateinit var permission: String
    private lateinit var pendingAction: QsbAction

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val permissionExtra = intent.getStringExtra(EXTRA_PERMISSION)
        val actionExtra = IntentCompat.getSerializableExtra(intent, EXTRA_ACTION, QsbAction::class.java)
        if (permissionExtra == null || actionExtra == null) {
            // Extras ausentes/corrompidos (não deveria acontecer — só
            // este arquivo constrói o Intent via newIntent()) — sem
            // dado suficiente para pedir nada, encerra sem travar o
            // usuário numa tela vazia.
            XaulinXsQsbPermissionCallback.clear()
            finish()
            return
        }
        permission = permissionExtra
        pendingAction = actionExtra

        ActivityCompat.requestPermissions(this, arrayOf(permission), REQUEST_CODE)
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray,
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != REQUEST_CODE) {
            finish()
            return
        }
        val granted = grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED
        if (granted) {
            XaulinXsQsbPermissionCallback.consumeIfGranted(pendingAction)
        } else {
            XaulinXsQsbPermissionCallback.clear()
        }
        finish()
    }

    companion object {
        private const val REQUEST_CODE = 7101
        private const val EXTRA_PERMISSION = "xaulinxs_qsb_permission"
        private const val EXTRA_ACTION = "xaulinxs_qsb_action"

        @JvmStatic
        fun newIntent(context: Context, permission: String, action: QsbAction): Intent =
            Intent(context, XaulinXsQsbPermissionActivity::class.java).apply {
                putExtra(EXTRA_PERMISSION, permission)
                putExtra(EXTRA_ACTION, action)
            }
    }
}
