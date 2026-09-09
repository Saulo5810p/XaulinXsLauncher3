/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Activity "ponte": abre o seletor de imagens do sistema assim que é criada, e
 * salva a imagem escolhida como ícone customizado do componente recebido via
 * intent extra. Não tem UI própria - existe só pra dar um alvo de Activity ao
 * toque no ícone do popup de app (mesmo padrão já usado e confirmado pelo
 * usuário em WallpaperPickerActivity: android.app.Activity puro, não
 * AppCompat/ComponentActivity, por isso startActivityForResult clássico em vez
 * da Activity Result API do androidx).
 */
package com.xaulinxs.customizations.apps

import android.app.Activity
import android.content.ComponentName
import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.util.Log
import com.android.launcher3.util.Executors

private const val REQUEST_CODE_PICK_ICON = 4178
const val EXTRA_TARGET_COMPONENT = "xaulinxs_target_component"

class AppIconPickerActivity : Activity() {

    private var targetComponent: ComponentName? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        targetComponent = intent?.getParcelableExtra(EXTRA_TARGET_COMPONENT)
        if (targetComponent == null) {
            finish()
            return
        }
        val pickIntent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "image/*"
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        startActivityForResult(pickIntent, REQUEST_CODE_PICK_ICON)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQUEST_CODE_PICK_ICON) {
            val uri: Uri? = data?.data
            val component = targetComponent
            if (resultCode == RESULT_OK && uri != null && component != null) {
                val appContext = applicationContext
                Executors.THREAD_POOL_EXECUTOR.execute {
                    try {
                        val bitmap = appContext.contentResolver.openInputStream(uri)?.use {
                            BitmapFactory.decodeStream(it)
                        }
                        if (bitmap != null) {
                            XaulinXsAppOverrides.setCustomIcon(appContext, component, bitmap)
                        }
                    } catch (e: Exception) {
                        Log.w("AppIconPickerActivity", "Não foi possível trocar o ícone do app", e)
                    }
                }
            }
        }
        finish()
    }
}
