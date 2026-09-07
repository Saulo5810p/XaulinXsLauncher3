/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Activity "ponte": abre o seletor de imagens do sistema assim que é
 * criada, e repassa a imagem escolhida pro XaulinXsInAppWallpaper. Não
 * tem UI própria — existe só pra dar um alvo de <intent> pra Preference
 * "Trocar wallpaper" (mesmo padrão de GridSizePickerActivity/
 * QsbConfigActivity: uma Activity dedicada por trás de uma Preference).
 *
 * android.app.Activity puro (não AppCompat/ComponentActivity) — mesma
 * razão documentada em GridSizePickerActivity — por isso usa
 * startActivityForResult clássico em vez da Activity Result API do
 * androidx, que exige ComponentActivity.
 */
package com.xaulinxs.customizations.settings

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import com.xaulinxs.customizations.theme.XaulinXsInAppWallpaper

private const val REQUEST_CODE_PICK_IMAGE = 4177

class WallpaperPickerActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "image/*"
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        startActivityForResult(intent, REQUEST_CODE_PICK_IMAGE)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQUEST_CODE_PICK_IMAGE) {
            val uri: Uri? = data?.data
            if (resultCode == RESULT_OK && uri != null) {
                // XaulinXs: troca partiu de uma ação explícita do usuário
                // dentro do R's Home3 — por isso alsoUpdateSystemWallpaper
                // = true, exatamente como pedido no info.txt ("aí sim o
                // papel de parede do sistema e do Launcher mudam").
                XaulinXsInAppWallpaper.setWallpaperFromUri(
                    applicationContext,
                    uri,
                    alsoUpdateSystemWallpaper = true,
                )
            }
        }
        finish()
    }
}
