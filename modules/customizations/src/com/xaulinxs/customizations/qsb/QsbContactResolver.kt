/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Resolve um nome de contato digitado no Modo Texto ("manda whatsapp
 * pra Ana") para um número de telefone real, via ContactsContract.
 *
 * Exige android.permission.READ_CONTACTS (adicionada ao Manifest por
 * este mesmo pacote de mudanças). Sem a permissão concedida, retorna
 * null e o chamador cai para o fluxo de pedir a permissão — nunca
 * finge sucesso nem usa dado incompleto.
 */
package com.xaulinxs.customizations.qsb

import android.content.Context
import android.content.pm.PackageManager
import android.provider.ContactsContract
import androidx.core.content.ContextCompat

object QsbContactResolver {

    data class ResolvedContact(val displayName: String, val phoneNumber: String)

    @JvmStatic
    fun hasContactsPermission(context: Context): Boolean =
        ContextCompat.checkSelfPermission(context, android.Manifest.permission.READ_CONTACTS) ==
            PackageManager.PERMISSION_GRANTED

    /**
     * Busca por nome (contém, case-insensitive) no provedor de
     * contatos. Retorna o primeiro contato com telefone cadastrado que
     * bate com [query], priorizando match exato de nome sobre "contém".
     * Retorna null se não tiver permissão, não achar nada, ou o
     * contato encontrado não tiver telefone.
     */
    @JvmStatic
    fun resolve(context: Context, query: String): ResolvedContact? {
        if (!hasContactsPermission(context)) return null
        if (query.isBlank()) return null

        val resolver = context.contentResolver
        val projection =
            arrayOf(
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                ContactsContract.CommonDataKinds.Phone.NUMBER,
            )
        val selection = "${ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME} LIKE ?"
        val selectionArgs = arrayOf("%$query%")

        var exactMatch: ResolvedContact? = null
        var containsMatch: ResolvedContact? = null
        val queryLower = query.trim().lowercase()

        resolver
            .query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                projection,
                selection,
                selectionArgs,
                null,
            )
            ?.use { cursor ->
                val nameIndex = cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME)
                val numberIndex = cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER)
                if (nameIndex < 0 || numberIndex < 0) return@use

                while (cursor.moveToNext()) {
                    val name = cursor.getString(nameIndex) ?: continue
                    val number = cursor.getString(numberIndex) ?: continue
                    val candidate = ResolvedContact(name, number)

                    if (name.trim().lowercase() == queryLower) {
                        exactMatch = candidate
                        // Match exato é o melhor resultado possível — não
                        // precisa continuar varrendo o cursor.
                        return@use
                    }
                    if (containsMatch == null) {
                        containsMatch = candidate
                    }
                }
            }

        return exactMatch ?: containsMatch
    }
}
