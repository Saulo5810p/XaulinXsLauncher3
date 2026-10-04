/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.misc.music

import android.content.ContentUris
import android.net.Uri
import android.provider.MediaStore

data class XaulinXsAudioTrack(
    val id: Long,
    val title: String,
    val artist: String,
    val album: String,
    val albumId: Long,
    val folder: String,
    val durationMs: Long,
    /** Nomes das playlists (MediaStore) em que a faixa está — usado só na busca. */
    val playlists: List<String>,
) {
    val uri: Uri
        get() = ContentUris.withAppendedId(MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, id)

    /** Texto único, já em minúsculas, para a busca global. */
    val searchBlob: String =
        "$title\n$artist\n$album\n$folder\n${playlists.joinToString("\n")}".lowercase()
}
