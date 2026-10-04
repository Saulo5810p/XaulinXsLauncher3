/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Widget grande: barra de pesquisa global no topo (faixa, artista, álbum,
 * pasta, playlist) + lista única, rolável na vertical, de todos os áudios.
 */
package com.xaulinxs.customizations.misc.music

import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.text.Editable
import android.text.TextWatcher
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.xaulinxs.customizations.misc.XaulinXsMiscPermissionActivity
import com.xaulinxs.customizations.misc.XaulinXsMiscPermissions
import java.util.concurrent.Executors

class XaulinXsMusicListWidget(context: Context) : LinearLayout(context), XaulinXsPlayer.Listener {

    private val search = EditText(context)
    private val recycler = XaulinXsNestedRecyclerView(context)
    private val empty = TextView(context)
    private val permissionButton = Button(context)
    private val adapter = TrackAdapter()

    private var all: List<XaulinXsAudioTrack> = emptyList()
    private var filtered: List<XaulinXsAudioTrack> = emptyList()
    private val io = Executors.newSingleThreadExecutor()
    private val permListener = Runnable { reload() }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    init {
        orientation = VERTICAL
        background = GradientDrawable().apply {
            setColor(Color.argb(150, 20, 20, 24))
            cornerRadius = dp(24).toFloat()
        }
        setPadding(dp(12), dp(12), dp(12), dp(8))

        search.apply {
            hint = "Pesquisar faixa, artista, álbum, pasta ou playlist"
            setSingleLine()
            setTextColor(Color.WHITE)
            setHintTextColor(Color.argb(160, 255, 255, 255))
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 15f)
            setPadding(dp(16), dp(10), dp(16), dp(10))
            background = GradientDrawable().apply {
                setColor(Color.argb(70, 255, 255, 255))
                cornerRadius = dp(22).toFloat()
            }
            addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
                override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
                override fun afterTextChanged(s: Editable?) = applyFilter()
            })
        }
        addView(search, LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        empty.apply {
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            visibility = GONE
        }
        permissionButton.apply {
            text = "Permitir acesso aos áudios"
            visibility = GONE
            setOnClickListener {
                XaulinXsMiscPermissionActivity.request(context, XaulinXsMiscPermissions.AUDIO)
            }
        }

        recycler.layoutManager = LinearLayoutManager(context)
        recycler.adapter = adapter
        recycler.overScrollMode = OVER_SCROLL_NEVER
        val lp = LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f)
        lp.topMargin = dp(8)
        addView(recycler, lp)
        addView(empty, LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        addView(permissionButton, LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT)
            .apply { gravity = Gravity.CENTER_HORIZONTAL })
    }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        XaulinXsPlayer.addListener(this)
        XaulinXsMiscPermissions.addListener(permListener)
        reload()
    }

    override fun onDetachedFromWindow() {
        XaulinXsPlayer.removeListener(this)
        XaulinXsMiscPermissions.removeListener(permListener)
        super.onDetachedFromWindow()
    }

    private fun reload() {
        if (!XaulinXsMiscPermissions.hasAudio(context)) {
            all = emptyList(); filtered = emptyList(); adapter.notifyDataSetChanged()
            empty.text = "Sem acesso aos áudios do aparelho."
            empty.visibility = VISIBLE
            permissionButton.visibility = VISIBLE
            return
        }
        permissionButton.visibility = GONE
        io.execute {
            val loaded = XaulinXsMusicRepository.loadAll(context.applicationContext)
            post { all = loaded; applyFilter() }
        }
    }

    private fun applyFilter() {
        val q = search.text.toString().trim().lowercase()
        filtered = if (q.isEmpty()) all else all.filter { it.searchBlob.contains(q) }
        adapter.notifyDataSetChanged()
        val showEmpty = filtered.isEmpty() && XaulinXsMiscPermissions.hasAudio(context)
        empty.text = if (all.isEmpty()) "Nenhum áudio encontrado." else "Nada encontrado para a pesquisa."
        empty.visibility = if (showEmpty) VISIBLE else GONE
    }

    override fun onPlayerStateChanged() {
        adapter.notifyDataSetChanged()
    }

    private inner class TrackAdapter : RecyclerView.Adapter<RecyclerView.ViewHolder>() {
        override fun getItemCount() = filtered.size

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
            val row = LinearLayout(parent.context).apply {
                orientation = VERTICAL
                setPadding(dp(12), dp(8), dp(12), dp(8))
                layoutParams = RecyclerView.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT,
                )
            }
            val title = TextView(parent.context).apply {
                setTextColor(Color.WHITE); setSingleLine(); setTypeface(typeface, Typeface.BOLD)
                setTextSize(TypedValue.COMPLEX_UNIT_SP, 15f)
                ellipsize = android.text.TextUtils.TruncateAt.END
            }
            val sub = TextView(parent.context).apply {
                setTextColor(Color.argb(190, 255, 255, 255)); setSingleLine()
                setTextSize(TypedValue.COMPLEX_UNIT_SP, 12f)
                ellipsize = android.text.TextUtils.TruncateAt.END
            }
            row.addView(title); row.addView(sub)
            return object : RecyclerView.ViewHolder(row) {}
        }

        override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
            val t = filtered[position]
            val row = holder.itemView as LinearLayout
            val title = row.getChildAt(0) as TextView
            val sub = row.getChildAt(1) as TextView
            val playing = XaulinXsPlayer.current?.id == t.id
            title.text = (if (playing) "▶ " else "") + t.title
            sub.text = "${t.artist} • ${t.album}"
            row.setOnClickListener {
                // A fila é a lista filtrada atual: "próxima" respeita a pesquisa.
                XaulinXsPlayer.playQueue(context, filtered, position)
            }
        }
    }
}
