/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * SeekBar para dentro do Workspace. Sem isso, o PagedView (troca de página na horizontal)
 * e o AllAppsSwipeController (vertical) interceptam o arrasto antes do slider reagir.
 * No toque inicial pedimos aos pais que não interceptem; o slider é dono do gesto até soltar.
 */
package com.xaulinxs.customizations.misc.music

import android.content.Context
import android.view.MotionEvent
import android.widget.SeekBar

class XaulinXsSeekBar(context: Context) : SeekBar(context) {

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (event.actionMasked == MotionEvent.ACTION_DOWN) {
            parent?.requestDisallowInterceptTouchEvent(true)
        }
        return super.onTouchEvent(event)
    }
}
