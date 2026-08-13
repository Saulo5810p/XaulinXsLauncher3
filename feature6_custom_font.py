"""
XaulinXs Customizations — Feature 6: Fonte customizada (TTF/OTF) com file
manager próprio (mesmo fluxo já validado no XaulinXs LatinIME).
Idempotente.
"""
from pathlib import Path

def write_if_absent(path_str, content):
    path = Path(path_str)
    if path.exists():
        print(f"SKIP (já existe): {path_str}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"CRIADO: {path_str}")

def replace_once(path_str, old, new, label):
    path = Path(path_str)
    assert path.exists(), f"arquivo não encontrado: {path_str}"
    content = path.read_text(encoding="utf-8")
    if new in content:
        print(f"SKIP ({label}): já aplicado")
        return
    assert old in content, f"âncora não encontrada em {path_str} ({label}) — cola o arquivo de novo"
    assert content.count(old) == 1, f"âncora aparece mais de uma vez em {path_str} ({label})"
    content = content.replace(old, new)
    path.write_text(content, encoding="utf-8")
    print(f"APLICADO: {label}")


write_if_absent(
    "modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsCustomFont.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Storage + carregamento da fonte customizada (TTF/OTF) importada pelo
 * usuário via XaulinXsFontFileManagerActivity. Mesmo princípio do projeto
 * irmão XaulinXs LatinIME: guarda o CAMINHO INTERNO (já copiado para
 * filesDir/xaulinxs_fonts/ pelo próprio file manager), nunca o caminho
 * externo original, e cacheia o Typeface já carregado em memória — este
 * método é chamado no hot path de desenho de cada label de ícone.
 */
package com.xaulinxs.customizations.font

import android.content.Context
import android.graphics.Typeface
import android.util.Log
import com.android.launcher3.ConstantItem
import com.android.launcher3.EncryptionType
import com.android.launcher3.LauncherPrefs
import java.io.File

object XaulinXsCustomFont {

    private const val TAG = "XaulinXsCustomFont"

    // Sem backedUpItem() aqui de propósito: o default é null, e
    // ConstantItem deriva `type` de `defaultValue!!::class.java` por
    // padrão — com null isso daria NPE, então o `type` precisa ser
    // explícito (mesmo padrão usado em NON_FIXED_LANDSCAPE_GRID_NAME no
    // LauncherPrefs.kt original).
    val CUSTOM_FONT_PATH: ConstantItem<String?> = ConstantItem(
        sharedPrefKey = "xaulinxs_custom_font_path",
        isBackedUp = true,
        defaultValue = null,
        encryptionType = EncryptionType.ENCRYPTED,
        type = String::class.java,
    )

    @Volatile private var cachedTypeface: Typeface? = null
    @Volatile private var cachedTypefacePath: String? = null

    @JvmStatic
    fun getCustomFontPath(context: Context): String? =
        LauncherPrefs.get(context).get(CUSTOM_FONT_PATH)

    @JvmStatic
    fun setCustomFontPath(context: Context, path: String?) {
        LauncherPrefs.get(context).put(CUSTOM_FONT_PATH, path)
        cachedTypeface = null
        cachedTypefacePath = null
    }

    /**
     * Carrega a fonte customizada do disco, se configurada e o arquivo
     * ainda existir. Nunca lança exceção — quem chamar sempre pode recair
     * no Typeface padrão da view.
     */
    @JvmStatic
    fun loadTypefaceIfAvailable(context: Context): Typeface? {
        val path = getCustomFontPath(context)
        if (path == null) {
            cachedTypeface = null
            cachedTypefacePath = null
            return null
        }
        cachedTypeface?.let { if (path == cachedTypefacePath) return it }

        val file = File(path)
        if (!file.isFile) {
            Log.w(TAG, "Custom font file no longer exists: $path")
            cachedTypeface = null
            cachedTypefacePath = null
            return null
        }
        return try {
            val typeface = Typeface.createFromFile(file)
            cachedTypeface = typeface
            cachedTypefacePath = path
            typeface
        } catch (e: Exception) {
            Log.w(TAG, "Failed to load custom font from $path", e)
            cachedTypeface = null
            cachedTypefacePath = null
            null
        }
    }
}
''',
)

write_if_absent(
    "modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsStoragePermissionHelper.kt",
    '''/*
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
import androidx.appcompat.app.AlertDialog
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
''',
)

write_if_absent(
    "modules/customizations/src/com/xaulinxs/customizations/font/XaulinXsFontFileManagerActivity.kt",
    '''/*
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
''',
)

write_if_absent(
    "res/layout/xaulinxs_filemanager_activity.xml",
    '''<?xml version="1.0" encoding="utf-8"?>
<!-- XaulinXs Customizations: file manager próprio para importar fonte TTF/OTF. -->
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical">

    <TextView
        android:id="@+id/xaulinxs_fm_current_path"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:padding="12dp"
        android:background="#11000000"
        android:textSize="12sp"
        android:singleLine="true"
        android:ellipsize="start" />

    <Button
        android:id="@+id/xaulinxs_fm_button_up"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="@string/xaulinxs_filemanager_up" />

    <TextView
        android:id="@+id/xaulinxs_fm_empty_label"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:padding="24dp"
        android:gravity="center"
        android:text="@string/xaulinxs_filemanager_empty"
        android:visibility="gone" />

    <ListView
        android:id="@+id/xaulinxs_fm_list"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1" />

</LinearLayout>
''',
)

write_if_absent(
    "res/layout/xaulinxs_filemanager_item.xml",
    '''<?xml version="1.0" encoding="utf-8"?>
<TextView xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:padding="16dp"
    android:textSize="15sp"
    android:background="?android:attr/selectableItemBackground" />
''',
)

write_if_absent(
    "modules/customizations/src/com/xaulinxs/customizations/settings/CustomFontPreference.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Diálogo com duas ações: "Importar fonte" (abre o file manager próprio
 * via startActivityForResult) e "Restaurar padrão" (limpa a fonte
 * customizada). O resultado da importação chega via
 * LauncherSettingsFragment.onActivityResult (ver SettingsActivity.java),
 * que repassa para handleActivityResult() abaixo.
 */
package com.xaulinxs.customizations.settings

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.util.AttributeSet
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.preference.Preference
import androidx.preference.PreferenceFragmentCompat
import com.android.launcher3.R
import com.xaulinxs.customizations.font.XaulinXsCustomFont
import com.xaulinxs.customizations.font.XaulinXsFontFileManagerActivity
import java.io.File

class CustomFontPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : Preference(context, attrs) {

    init {
        isPersistent = false
        updateSummary()
    }

    override fun onClick() {
        AlertDialog.Builder(context)
            .setTitle(R.string.xaulinxs_custom_font_title)
            .setMessage(currentFontLabel())
            .setPositiveButton(R.string.xaulinxs_font_choose) { _, _ -> launchFontPicker() }
            .setNeutralButton(R.string.xaulinxs_font_reset) { _, _ ->
                XaulinXsCustomFont.setCustomFontPath(context, null)
                updateSummary()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun launchFontPicker() {
        val intent = Intent(context, XaulinXsFontFileManagerActivity::class.java)
        try {
            (context as? Activity)?.startActivityForResult(intent, REQUEST_CODE_PICK_FONT)
        } catch (e: Exception) {
            Toast.makeText(context, R.string.xaulinxs_filemanager_import_error, Toast.LENGTH_SHORT).show()
        }
    }

    fun onFontImported(path: String) {
        XaulinXsCustomFont.setCustomFontPath(context, path)
        updateSummary()
    }

    private fun currentFontLabel(): String {
        val path = XaulinXsCustomFont.getCustomFontPath(context)
        return if (path == null) {
            context.getString(R.string.xaulinxs_font_none)
        } else {
            context.getString(R.string.xaulinxs_font_current, File(path).name)
        }
    }

    private fun updateSummary() {
        summary = currentFontLabel()
    }

    companion object {
        const val REQUEST_CODE_PICK_FONT = 7001
        private const val PREF_KEY = "xaulinxs_custom_font"

        @JvmStatic
        fun handleActivityResult(
            fragment: PreferenceFragmentCompat,
            requestCode: Int,
            resultCode: Int,
            data: Intent?,
        ) {
            if (requestCode != REQUEST_CODE_PICK_FONT || resultCode != Activity.RESULT_OK || data == null) return
            val path = data.getStringExtra(XaulinXsFontFileManagerActivity.EXTRA_SELECTED_FONT_PATH) ?: return
            (fragment.findPreference(PREF_KEY) as? CustomFontPreference)?.onFontImported(path)
        }
    }
}
''',
)

replace_once(
    "src/com/android/launcher3/BubbleTextView.java",
    old='''        mIconSize = a.getDimensionPixelSize(R.styleable.BubbleTextView_iconSizeOverride,
                defaultIconSize);
        a.recycle();

        mRunningAppIndicatorHeight =''',
    new='''        mIconSize = a.getDimensionPixelSize(R.styleable.BubbleTextView_iconSizeOverride,
                defaultIconSize);
        a.recycle();

        // XaulinXs Customizations: aplica fonte customizada (TTF/OTF) importada
        // pelo usuário ao label do ícone, se houver uma configurada.
        android.graphics.Typeface xaulinxsCustomTypeface =
                com.xaulinxs.customizations.font.XaulinXsCustomFont.loadTypefaceIfAvailable(context);
        if (xaulinxsCustomTypeface != null) {
            setTypeface(xaulinxsCustomTypeface);
        }

        mRunningAppIndicatorHeight =''',
    label="BubbleTextView aplica fonte customizada nos labels",
)

replace_once(
    "src/com/android/launcher3/settings/SettingsActivity.java",
    old='''        @Override
        public void onCreatePreferences(Bundle savedInstanceState, String rootKey) {''',
    new='''        @Override
        public void onActivityResult(int requestCode, int resultCode, Intent data) {
            super.onActivityResult(requestCode, resultCode, data);
            // XaulinXs Customizations: repassa o resultado da escolha de fonte
            // customizada (Activity separada) para a preference que sabe salvar
            // e atualizar o resumo.
            com.xaulinxs.customizations.settings.CustomFontPreference.handleActivityResult(
                    this, requestCode, resultCode, data);
        }

        @Override
        public void onCreatePreferences(Bundle savedInstanceState, String rootKey) {''',
    label="LauncherSettingsFragment.onActivityResult repassa para CustomFontPreference",
)

replace_once(
    "res/xml/launcher_preferences.xml",
    old='''        <com.xaulinxs.customizations.settings.ManualColorPickerPreference
            android:key="xaulinxs_manual_color_picker"
            android:title="@string/xaulinxs_manual_color_picker_title"
            android:persistent="false" />

    </PreferenceScreen>''',
    new='''        <com.xaulinxs.customizations.settings.ManualColorPickerPreference
            android:key="xaulinxs_manual_color_picker"
            android:title="@string/xaulinxs_manual_color_picker_title"
            android:persistent="false" />

        <com.xaulinxs.customizations.settings.CustomFontPreference
            android:key="xaulinxs_custom_font"
            android:title="@string/xaulinxs_custom_font_title"
            android:persistent="false" />

    </PreferenceScreen>''',
    label="launcher_preferences.xml com o item de fonte customizada",
)

replace_once(
    "res/values/xaulinxs_strings.xml",
    old='''    <string name="xaulinxs_manual_color_save">Salvar</string>
</resources>''',
    new='''    <string name="xaulinxs_manual_color_save">Salvar</string>
    <string name="xaulinxs_custom_font_title">Fonte customizada dos ícones</string>
    <string name="xaulinxs_font_choose">Importar fonte (.ttf/.otf)</string>
    <string name="xaulinxs_font_current">Fonte atual: %1$s</string>
    <string name="xaulinxs_font_none">Fonte atual: padrão do sistema</string>
    <string name="xaulinxs_font_reset">Restaurar padrão</string>
    <string name="xaulinxs_filemanager_title">Escolher arquivo de fonte</string>
    <string name="xaulinxs_filemanager_empty">Nenhum arquivo .ttf/.otf encontrado nesta pasta</string>
    <string name="xaulinxs_filemanager_up">Pasta anterior</string>
    <string name="xaulinxs_filemanager_import_error">Não foi possível importar esta fonte</string>
    <string name="xaulinxs_storage_permission_title">Acesso aos arquivos</string>
    <string name="xaulinxs_storage_permission_message">Para navegar suas pastas e importar uma fonte, o app precisa de permissão de acesso a todos os arquivos do dispositivo. Você será levado à tela de configurações do sistema para conceder esse acesso.</string>
    <string name="xaulinxs_storage_permission_grant">Conceder acesso</string>
    <string name="xaulinxs_storage_permission_deny">Agora não</string>
    <string name="xaulinxs_storage_permission_error">Não foi possível abrir as configurações de permissão</string>
</resources>''',
    label="strings da fonte customizada",
)

replace_once(
    "AndroidManifest.xml",
    old='''    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />''',
    new='''    <!-- XaulinXs Customizations: acesso a todos os arquivos, necessário para o
         file manager próprio navegar livremente o armazenamento e importar
         fontes TTF/OTF de qualquer pasta.
         - MANAGE_EXTERNAL_STORAGE: Android 11+ (API 30+), concedida via tela
           especial do sistema (ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION).
         - WRITE_EXTERNAL_STORAGE com maxSdkVersion=29: cobre minSdk 28-29 via
           diálogo padrão de runtime permission (API 23+). READ_EXTERNAL_STORAGE
           já existe acima sem maxSdkVersion, então não precisa duplicar. -->
    <uses-permission android:name="android.permission.MANAGE_EXTERNAL_STORAGE"
        tools:ignore="ScopedStorage" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"
        android:maxSdkVersion="29" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />''',
    label="permissões de armazenamento no AndroidManifest.xml",
)

replace_once(
    "AndroidManifest.xml",
    old='''            android:name="com.android.launcher3.settings.SettingsActivity"''',
    new='''            android:name="com.xaulinxs.customizations.font.XaulinXsFontFileManagerActivity"
            android:theme="@style/HomeSettings.Theme"
            android:label="@string/xaulinxs_filemanager_title"
            android:exported="false" />
        <activity
            android:name="com.android.launcher3.settings.SettingsActivity"''',
    label="XaulinXsFontFileManagerActivity registrada no AndroidManifest.xml",
)

print("\nFeature 6 aplicada com sucesso.")
