/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Lê TODOS os áudios do armazenamento via MediaStore. Não filtra por extensão:
 * o que o MediaStore indexa (wav, flac, mp3, m4a, opus, alac, ogg, webm, ...)
 * é o que o Android sabe tocar, então a lista acompanha o suporte do aparelho.
 * Só descarta entradas pendentes/sem duração.
 */
package com.xaulinxs.customizations.misc.music

import android.content.ContentUris
import android.content.Context
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import java.io.File

object XaulinXsMusicRepository {

    fun loadAll(context: Context): List<XaulinXsAudioTrack> {
        val playlistsByAudio = loadPlaylistMembership(context)
        val out = ArrayList<XaulinXsAudioTrack>()

        val projection = buildList {
            add(MediaStore.Audio.Media._ID)
            add(MediaStore.Audio.Media.TITLE)
            add(MediaStore.Audio.Media.ARTIST)
            add(MediaStore.Audio.Media.ALBUM)
            add(MediaStore.Audio.Media.ALBUM_ID)
            add(MediaStore.Audio.Media.DURATION)
            add(MediaStore.Audio.Media.DISPLAY_NAME)
            add(MediaStore.Audio.Media.DATA)
            if (Build.VERSION.SDK_INT >= 29) add(MediaStore.Audio.Media.RELATIVE_PATH)
        }.toTypedArray()

        val sel = if (Build.VERSION.SDK_INT >= 29) "${MediaStore.Audio.Media.IS_PENDING}=0" else null

        try {
            context.contentResolver.query(
                MediaStore.Audio.Media.EXTERNAL_CONTENT_URI,
                projection,
                sel,
                null,
                "${MediaStore.Audio.Media.TITLE} COLLATE NOCASE ASC",
            )?.use { c ->
                val iId = c.getColumnIndexOrThrow(MediaStore.Audio.Media._ID)
                val iTitle = c.getColumnIndexOrThrow(MediaStore.Audio.Media.TITLE)
                val iArtist = c.getColumnIndexOrThrow(MediaStore.Audio.Media.ARTIST)
                val iAlbum = c.getColumnIndexOrThrow(MediaStore.Audio.Media.ALBUM)
                val iAlbumId = c.getColumnIndexOrThrow(MediaStore.Audio.Media.ALBUM_ID)
                val iDur = c.getColumnIndexOrThrow(MediaStore.Audio.Media.DURATION)
                val iName = c.getColumnIndexOrThrow(MediaStore.Audio.Media.DISPLAY_NAME)
                val iData = c.getColumnIndex(MediaStore.Audio.Media.DATA)
                val iRel = if (Build.VERSION.SDK_INT >= 29)
                    c.getColumnIndex(MediaStore.Audio.Media.RELATIVE_PATH) else -1

                while (c.moveToNext()) {
                    val id = c.getLong(iId)
                    val duration = c.getLong(iDur)
                    if (duration <= 0L) continue
                    val rawTitle = c.getString(iTitle)
                    val title = if (rawTitle.isNullOrBlank())
                        c.getString(iName)?.substringBeforeLast('.') ?: "?" else rawTitle
                    val artist = c.getString(iArtist).cleanUnknown("Artista desconhecido")
                    val album = c.getString(iAlbum).cleanUnknown("Álbum desconhecido")
                    val folder = folderOf(
                        if (iRel >= 0) c.getString(iRel) else null,
                        if (iData >= 0) c.getString(iData) else null,
                    )
                    out.add(
                        XaulinXsAudioTrack(
                            id, title, artist, album, c.getLong(iAlbumId),
                            folder, duration, playlistsByAudio[id] ?: emptyList(),
                        ),
                    )
                }
            }
        } catch (_: SecurityException) {
            // Sem permissão de áudio ainda: devolve lista vazia, a UI mostra o botão de permitir.
        }
        return out
    }

    private fun String?.cleanUnknown(fallback: String): String =
        if (isNullOrBlank() || this == "<unknown>") fallback else this

    private fun folderOf(relativePath: String?, data: String?): String {
        if (!relativePath.isNullOrBlank()) {
            return relativePath.trimEnd('/').substringAfterLast('/')
        }
        if (!data.isNullOrBlank()) return File(data).parentFile?.name ?: ""
        return ""
    }

    /** audioId -> nomes das playlists. Best-effort: playlists são APIs antigas do MediaStore. */
    @Suppress("DEPRECATION")
    private fun loadPlaylistMembership(context: Context): Map<Long, List<String>> {
        val map = HashMap<Long, MutableList<String>>()
        try {
            val resolver = context.contentResolver
            resolver.query(
                MediaStore.Audio.Playlists.EXTERNAL_CONTENT_URI,
                arrayOf(MediaStore.Audio.Playlists._ID, MediaStore.Audio.Playlists.NAME),
                null, null, null,
            )?.use { pl ->
                while (pl.moveToNext()) {
                    val plId = pl.getLong(0)
                    val plName = pl.getString(1) ?: continue
                    val membersUri: Uri = MediaStore.Audio.Playlists.Members
                        .getContentUri("external", plId)
                    resolver.query(
                        membersUri,
                        arrayOf(MediaStore.Audio.Playlists.Members.AUDIO_ID),
                        null, null, null,
                    )?.use { m ->
                        while (m.moveToNext()) {
                            map.getOrPut(m.getLong(0)) { ArrayList() }.add(plName)
                        }
                    }
                }
            }
        } catch (_: Exception) {
            // Sem acesso a playlists: a busca por playlist simplesmente não acha nada.
        }
        return map
    }

    fun albumArtUri(albumId: Long): Uri =
        ContentUris.withAppendedId(Uri.parse("content://media/external/audio/albumart"), albumId)
}
