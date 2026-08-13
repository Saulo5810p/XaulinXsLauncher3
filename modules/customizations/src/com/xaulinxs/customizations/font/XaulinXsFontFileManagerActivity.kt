/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * File manager próprio para navegação real do armazenamento via
 * java.io.File, filtrando por pastas e arquivos de fonte (.ttf/.otf), sem
 * depender de um seletor de sistema. Porte direto do
 * FontFileManagerActivity do projeto irmão XaulinXs LatinIME (já validado
 * lá), só trocando o pacote de R e a subpasta interna de destino.
 *
 * A fonte escolhida é copiada para a pasta interna do app (nunca lida
 * diretamente do caminho externo em uso contínuo), para que os ícones
 * continuem com a fonte aplicada mesmo se o arquivo original for movido,
 * apagado, ou se a permissão de armazenamento for revogada depois.
 */
package com.xaulinxs.customizations.font

import android.app.Activity
import android.os.Bundle
import android.os.Environment
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.ListView
import android.widget.TextView
import android.widget.Toast
import com.android.launcher3.R
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.IOException
import java.util.Locale

class XaulinXsFontFileManagerActivity : Activity() {

    private lateinit var currentPathLabel: TextView
    private lateinit var emptyLabel: TextView
    private lateinit var listView: ListView
    private lateinit var buttonUp: Button

    private var currentDir: File? = null
    private val currentEntries = mutableListOf<File>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.xaulinxs_filemanager_activity)
        setTitle(R.string.xaulinxs_filemanager_title)

        currentPathLabel = findViewById(R.id.xaulinxs_fm_current_path)
        emptyLabel = findViewById(R.id.xaulinxs_fm_empty_label)
        listView = findViewById(R.id.xaulinxs_fm_list)
        buttonUp = findViewById(R.id.xaulinxs_fm_button_up)

        buttonUp.setOnClickListener { navigateUp() }
        listView.setOnItemClickListener { _, _, position, _ -> onEntryClicked(position) }

        if (!XaulinXsStoragePermissionHelper.hasStoragePermission(this)) {
            XaulinXsStoragePermissionHelper.requestStoragePermission(this)
            showEmptyState(true)
            return
        }
        openDirectory(Environment.getExternalStorageDirectory())
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == XaulinXsStoragePermissionHelper.REQUEST_CODE_MANAGE_STORAGE) {
            if (XaulinXsStoragePermissionHelper.hasStoragePermission(this)) {
                openDirectory(Environment.getExternalStorageDirectory())
            } else {
                Toast.makeText(this, R.string.xaulinxs_storage_permission_error, Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray,
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == XaulinXsStoragePermissionHelper.REQUEST_CODE_LEGACY_STORAGE) {
            if (XaulinXsStoragePermissionHelper.hasStoragePermission(this)) {
                openDirectory(Environment.getExternalStorageDirectory())
            } else {
                Toast.makeText(this, R.string.xaulinxs_storage_permission_error, Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun navigateUp() {
        val parent = currentDir?.parentFile ?: return
        if (parent.canRead()) openDirectory(parent)
    }

    private fun onEntryClicked(position: Int) {
        if (position < 0 || position >= currentEntries.size) return
        val entry = currentEntries[position]
        if (entry.isDirectory) openDirectory(entry) else importFontAndFinish(entry)
    }

    private fun openDirectory(dir: File) {
        try {
            val files = dir.listFiles()
            currentEntries.clear()
            if (files != null) {
                val directories = mutableListOf<File>()
                val fontFiles = mutableListOf<File>()
                for (f in files) {
                    if (f.isHidden) continue
                    if (f.isDirectory && f.canRead()) {
                        directories.add(f)
                    } else if (f.isFile && hasFontExtension(f.name)) {
                        fontFiles.add(f)
                    }
                }
                val byName = compareBy<File> { it.name.lowercase(Locale.ROOT) }
                directories.sortWith(byName)
                fontFiles.sortWith(byName)
                currentEntries.addAll(directories)
                currentEntries.addAll(fontFiles)
            }
            currentDir = dir
            currentPathLabel.text = dir.absolutePath

            val displayNames = currentEntries.map { f ->
                if (f.isDirectory) "[dir] " + f.name else f.name
            }
            listView.adapter = ArrayAdapter(this, R.layout.xaulinxs_filemanager_item, displayNames)
            showEmptyState(currentEntries.isEmpty())
        } catch (e: SecurityException) {
            currentEntries.clear()
            listView.adapter = ArrayAdapter(this, R.layout.xaulinxs_filemanager_item, emptyList<String>())
            showEmptyState(true)
        } catch (e: NullPointerException) {
            currentEntries.clear()
            listView.adapter = ArrayAdapter(this, R.layout.xaulinxs_filemanager_item, emptyList<String>())
            showEmptyState(true)
        }
    }

    private fun showEmptyState(empty: Boolean) {
        emptyLabel.visibility = if (empty) View.VISIBLE else View.GONE
        listView.visibility = if (empty) View.GONE else View.VISIBLE
    }

    private fun hasFontExtension(fileName: String): Boolean {
        val lower = fileName.lowercase(Locale.ROOT)
        return FONT_EXTENSIONS.any { lower.endsWith(it) }
    }

    private fun importFontAndFinish(sourceFile: File) {
        try {
            val fontsDir = File(filesDir, "xaulinxs_fonts")
            if (!fontsDir.exists() && !fontsDir.mkdirs()) {
                throw IOException("Failed to create fonts directory")
            }
            val destFile = File(fontsDir, sourceFile.name)
            copyFile(sourceFile, destFile)

            val result = android.content.Intent()
            result.putExtra(EXTRA_SELECTED_FONT_PATH, destFile.absolutePath)
            setResult(RESULT_OK, result)
            finish()
        } catch (e: IOException) {
            Toast.makeText(this, R.string.xaulinxs_filemanager_import_error, Toast.LENGTH_SHORT).show()
        } catch (e: SecurityException) {
            Toast.makeText(this, R.string.xaulinxs_filemanager_import_error, Toast.LENGTH_SHORT).show()
        }
    }

    private fun copyFile(source: File, dest: File) {
        FileInputStream(source).use { input ->
            FileOutputStream(dest).use { output ->
                val buffer = ByteArray(8192)
                var read: Int
                while (input.read(buffer).also { read = it } != -1) {
                    output.write(buffer, 0, read)
                }
            }
        }
    }

    companion object {
        const val EXTRA_SELECTED_FONT_PATH = "xaulinxs_selected_font_path"
        private val FONT_EXTENSIONS = arrayOf(".ttf", ".otf")
    }
}
