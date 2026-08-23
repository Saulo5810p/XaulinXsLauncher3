/*
 * Copyright (C) 2025 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.android.launcher3.display

import android.content.Context
import android.hardware.display.DisplayManager
import android.hardware.display.DisplayManager.DisplayListener
import android.os.Build
import android.util.Log
import android.util.SparseArray
import android.view.Display
import android.view.WindowManager.LayoutParams
import androidx.annotation.AnyThread
import androidx.core.util.forEach
import com.android.launcher3.Flags
import com.android.launcher3.dagger.ApplicationContext
import com.android.launcher3.dagger.LauncherAppSingleton
import com.android.launcher3.util.DaggerSingletonTracker
import com.android.launcher3.util.Executors
import com.android.launcher3.util.window.WindowManagerProxy
import java.io.PrintWriter
import java.util.concurrent.ConcurrentHashMap
import javax.inject.Inject

/** Utility class to cache properties of default display to avoid a system RPC on every call. */
@LauncherAppSingleton
class DisplayControllerImpl
@Inject
constructor(
    @ApplicationContext private val appContext: Context,
    private val wmProxy: WindowManagerProxy,
    overlayChangeHandler: OverlayChangeHandler,
    lifecycle: DaggerSingletonTracker,
) : DisplayController, DisplayListener {

    @Deprecated("Will replace it with threadSafePerDisplayInfo")
    private val perDisplayInfo = SparseArray<DisplayInfoContainer>()

    private val threadSafePerDisplayInfo = ConcurrentHashMap<Int, DisplayInfoContainer>()

    private val displayManager =
        requireNotNull(appContext.getSystemService(DisplayManager::class.java))

    init {
        lifecycle.addCloseable(
            overlayChangeHandler.addCallback { notifyConfigChange(Display.DEFAULT_DISPLAY) }
        )

        // Initialize display listeners
        displayManager.registerDisplayListener(this, Executors.MAIN_EXECUTOR.handler)
        // Add any PerDisplayInfos for already-connected displays.
        displayManager.displays.forEach { getOrCreatePerDisplayInfo(it) }
        getOrCreatePerDisplayInfo(displayManager.getDisplay(Display.DEFAULT_DISPLAY))

        lifecycle.addCloseable {
            displayManager.unregisterDisplayListener(this)
            if (Flags.enableTaskbarUiThread()) {
                threadSafePerDisplayInfo.forEach { (_, container) -> container.cleanup() }
            } else {
                perDisplayInfo.forEach { _, container -> container.cleanup() }
            }
        }
    }

    private fun getOrCreatePerDisplayInfo(display: Display): DisplayInfoContainer {
        val displayId = display.displayId
        return if (Flags.enableTaskbarUiThread()) {
            threadSafePerDisplayInfo.getOrPut(displayId) {
                createDisplayInfoContainer(display, displayId)
            }
        } else {
            perDisplayInfo[displayId]
                ?: createDisplayInfoContainer(display, displayId).apply {
                    perDisplayInfo[displayId] = this
                }
        }
    }

    private fun createDisplayInfoContainer(display: Display, displayId: Int): DisplayInfoContainer {
        if (DEBUG) {
            Log.d(TAG, "getOrCreatePerDisplayInfo - no cached value found for $displayId")
        }
        return DisplayInfoContainer(
            displayId,
            createWindowContextCompat(display),
            wmProxy,
        )
    }

    // XaulinXs fix (crash real confirmado via logcat de um Android 11 —
    // NoSuchMethodError, desde antes das features de customização):
    // createWindowContext(Display, int, Bundle) — a variante com Display
    // explícito — só existe a partir da API 31 (Android 12). No Android
    // 11 (API 30) essa assinatura de 3 argumentos não existe na classe
    // Context, e chamá-la incondicionalmente derruba o app com
    // NoSuchMethodError logo no Launcher.onCreate(), antes de qualquer
    // tela aparecer. Fix: em API 30, usar createDisplayContext(display)
    // seguido de createWindowContext(int, Bundle) — a combinação
    // documentada pela própria Android para obter um window context de
    // um display específico quando só a variante de 2 argumentos está
    // disponível. O projeto declara minSdk 28, mas mesmo
    // createWindowContext(int, Bundle) e Context.getDisplay() (usado
    // logo abaixo em DisplayInfoContainer) só existem a partir da API
    // 30 — abaixo disso exigiria uma reestruturação maior do
    // DisplayInfoContainer, fora do escopo deste crash específico.
    private fun createWindowContextCompat(display: Display): Context {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            appContext.createWindowContext(display, LayoutParams.TYPE_APPLICATION, null)
        } else {
            appContext
                .createDisplayContext(display)
                .createWindowContext(LayoutParams.TYPE_APPLICATION, null)
        }
    }

    @AnyThread
    override fun getPerDisplayInfoById(displayId: Int): DisplayInfoContainer? =
        if (Flags.enableTaskbarUiThread()) threadSafePerDisplayInfo[displayId]
        else perDisplayInfo[displayId]

    override fun onDisplayAdded(displayId: Int) {
        displayManager.getDisplay(displayId)?.let { getOrCreatePerDisplayInfo(it) }
    }

    override fun onDisplayChanged(displayId: Int) {}

    override fun onDisplayRemoved(displayId: Int) {
        if (Flags.enableTaskbarUiThread()) {
            threadSafePerDisplayInfo.remove(displayId)?.cleanup()
        } else {
            perDisplayInfo[displayId]?.cleanup()
            perDisplayInfo.remove(displayId)
        }
    }

    /** Dumps the current state information */
    override fun dump(pw: PrintWriter) {
        if (Flags.enableTaskbarUiThread()) {
            threadSafePerDisplayInfo.forEach { (displayId, container) ->
                dumpInternal(pw, displayId, container.info.value)
            }
        } else {
            perDisplayInfo.forEach { displayId, container ->
                dumpInternal(pw, displayId, container.info.value)
            }
        }
    }

    private fun dumpInternal(pw: PrintWriter, displayId: Int, info: LauncherDisplayInfo) {
        pw.println("DisplayController.Info (displayId=$displayId):")
        info.dump(pw)
    }

    companion object {
        private const val TAG = "DisplayControllerImpl"
        private const val DEBUG = false
    }
}
