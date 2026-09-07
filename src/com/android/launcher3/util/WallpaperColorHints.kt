/*
 * Copyright (C) 2023 The Android Open Source Project
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

package com.android.launcher3.util

import android.app.WallpaperColors
import android.app.WallpaperManager
import android.app.WallpaperManager.FLAG_SYSTEM
import android.app.WallpaperManager.OnColorsChangedListener
import android.content.Context
import androidx.annotation.MainThread
import androidx.annotation.VisibleForTesting
import com.android.launcher3.dagger.ApplicationContext
import com.android.launcher3.dagger.LauncherAppComponent
import com.android.launcher3.dagger.LauncherAppSingleton
import com.android.launcher3.util.Executors.MAIN_EXECUTOR
import com.android.launcher3.util.Executors.THREAD_POOL_EXECUTOR
import com.android.launcher3.util.Executors.UI_HELPER_EXECUTOR
import javax.inject.Inject

/**
 * This class caches the system's wallpaper color hints for use by other classes as a performance
 * enhancer. It also centralizes all the WallpaperManager color hint code in one location.
 *
 * XaulinXs Customizations (info.txt/etapa 3 — "unificar os dois pipelines
 * de cor pra seguir o nosso wallpaper próprio"): antes, [colors] sempre
 * vinha do wallpaper REAL do sistema (WallpaperManager, FLAG_SYSTEM). Como
 * o launcher agora tem um wallpaper próprio, desenhado por
 * XaulinXsWallpaperView e independente do sistema (ver
 * XaulinXsInAppWallpaper), todo o resto do launcher que consome esta
 * classe (ícones temáticos, scrim do drawer, cor dos balões, o efeito de
 * "vidro fosco") ficaria mostrando um tema de cor que não bate com o que
 * está na tela. [colors] agora prioriza a cor extraída do NOSSO wallpaper
 * (via WallpaperColors.fromBitmap, API pública) sempre que ele já foi
 * carregado; só cai de volta pro wallpaper real do sistema antes disso
 * (ex.: primeiríssimo frame, antes do arquivo padrão terminar de ser
 * copiado) ou se por algum motivo a extração falhar.
 */
@LauncherAppSingleton
class WallpaperColorHints
@Inject
constructor(@ApplicationContext private val context: Context, tracker: DaggerSingletonTracker) {

    private val wallpaperManager
        get() = context.getSystemService(WallpaperManager::class.java)!!

    private var systemColors: WallpaperColors? = wallpaperManager.getWallpaperColors(FLAG_SYSTEM)

    // XaulinXs: cor extraída do NOSSO wallpaper (armazenamento privado do
    // app) — calculada em background (WallpaperColors.fromBitmap não é
    // instantâneo) e cacheada até o wallpaper mudar de novo.
    @Volatile private var xaulinxsColors: WallpaperColors? = null

    /**
     * XaulinXs: cor efetiva usada pelo resto do launcher. Prioriza
     * [xaulinxsColors] (nosso wallpaper próprio); [systemColors] é só o
     * fallback enquanto [xaulinxsColors] ainda não foi calculada.
     */
    var colors: WallpaperColors?
        get() = xaulinxsColors ?: systemColors
        private set(value) {
            systemColors = value
        }

    val hints: Int
        get() = colors?.colorHints ?: 0

    private val onColorHintsChangedListeners = mutableListOf<OnColorHintListener>()

    init {
        val onColorsChangedListener = OnColorsChangedListener { changedColors, which ->
            onColorsChanged(changedColors, which)
        }
        UI_HELPER_EXECUTOR.execute {
            wallpaperManager.addOnColorsChangedListener(
                onColorsChangedListener,
                MAIN_EXECUTOR.handler,
            )
        }
        tracker.addCloseable {
            UI_HELPER_EXECUTOR.execute {
                wallpaperManager.removeOnColorsChangedListener(onColorsChangedListener)
            }
        }

        // XaulinXs: recalcula a cor do nosso wallpaper sempre que ele mudar
        // (primeira cópia do padrão, ou troca manual via "Trocar
        // wallpaper"), e já tenta uma vez de cara pro caso comum de o
        // arquivo já existir quando o launcher inicia.
        recomputeXaulinxsColors()
        com.xaulinxs.customizations.theme.XaulinXsInAppWallpaper.addOnChangedListener {
            recomputeXaulinxsColors()
        }
    }

    private fun recomputeXaulinxsColors() {
        THREAD_POOL_EXECUTOR.execute {
            val bitmap =
                com.xaulinxs.customizations.theme.XaulinXsInAppWallpaper.getCurrentWallpaper(
                    context
                ) ?: return@execute
            val extracted =
                try {
                    WallpaperColors.fromBitmap(bitmap)
                } catch (e: Exception) {
                    null
                } ?: return@execute
            MAIN_EXECUTOR.execute {
                val oldHints = hints
                xaulinxsColors = extracted
                val newHints = hints
                if (oldHints != newHints) {
                    onColorHintsChangedListeners.forEach { it.onColorHintsChanged(newHints) }
                }
            }
        }
    }

    @MainThread
    private fun onColorsChanged(changedColors: WallpaperColors?, which: Int) {
        if ((which and FLAG_SYSTEM) != 0) {
            val oldHints = hints
            colors = changedColors
            val newHints = hints
            if (oldHints != newHints) {
                onColorHintsChangedListeners.forEach { it.onColorHintsChanged(newHints) }
            }
        }
    }

    fun registerOnColorHintsChangedListener(listener: OnColorHintListener) {
        onColorHintsChangedListeners.add(listener)
    }

    fun unregisterOnColorsChangedListener(listener: OnColorHintListener) {
        onColorHintsChangedListeners.remove(listener)
    }

    companion object {
        @VisibleForTesting
        @JvmField
        val INSTANCE = DaggerSingletonObject(LauncherAppComponent::getWallpaperColorHints)

        @JvmStatic fun get(context: Context): WallpaperColorHints = INSTANCE.get(context)
    }
}

interface OnColorHintListener {
    fun onColorHintsChanged(colorHints: Int)
}
