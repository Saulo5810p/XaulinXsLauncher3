/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * RecyclerView para dentro do Workspace. O DragLayer tem um AllAppsSwipeController que
 * intercepta qualquer arrasto vertical na tela inicial (para abrir o menu de apps) ANTES
 * de o RecyclerView ver o movimento — por isso a lista não rolava.
 *
 * No ACTION_DOWN pedimos aos pais que não interceptem; assim o gesto vertical é da lista.
 * Se o dedo for mais na horizontal que na vertical, devolvemos o controle aos pais, para
 * o usuário continuar trocando de página do Workspace arrastando para os lados.
 */
package com.xaulinxs.customizations.misc.music

import android.content.Context
import android.view.MotionEvent
import android.view.ViewConfiguration
import androidx.recyclerview.widget.RecyclerView
import kotlin.math.abs

class XaulinXsNestedRecyclerView(context: Context) : RecyclerView(context) {

    private val slop = ViewConfiguration.get(context).scaledTouchSlop
    private var startX = 0f
    private var startY = 0f
    private var decided = false

    override fun dispatchTouchEvent(ev: MotionEvent): Boolean {
        when (ev.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                startX = ev.x
                startY = ev.y
                decided = false
                parent?.requestDisallowInterceptTouchEvent(true)
            }
            MotionEvent.ACTION_MOVE -> if (!decided) {
                val dx = abs(ev.x - startX)
                val dy = abs(ev.y - startY)
                if (dx > slop || dy > slop) {
                    decided = true
                    // Horizontal: o Workspace (PagedView) volta a poder interceptar e paginar.
                    if (dx > dy) parent?.requestDisallowInterceptTouchEvent(false)
                }
            }
        }
        return super.dispatchTouchEvent(ev)
    }
}
