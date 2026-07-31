/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Substitui a factory MonoIconThemeFactory do AOSP (mesmo MONO_FACTORY_ID,
 * para reaproveitar a preference/UI existente sem alteração) por uma versão
 * que usa XaulinXsThemedIconColors — cores extraídas de verdade do
 * wallpaper — em vez dos recursos estáticos que não funcionam neste device.
 */
package com.xaulinxs.customizations.icons

import com.android.launcher3.graphics.theme.IconThemeFactory
import com.android.launcher3.icons.IconThemeController
import com.android.launcher3.icons.mono.MonoIconThemeController
import com.android.launcher3.logging.StatsLogManager.LauncherEvent.LAUNCHER_THEMED_ICON_ENABLED
import com.android.launcher3.logging.StatsLogManager.StatsLogger

object XaulinXsMonoIconThemeFactory : IconThemeFactory {

    const val MONO_FACTORY_ID = "mono-icons"

    val MONO_THEME_CONTROLLER =
        MonoIconThemeController(
            shouldForceThemeIcon = true,
            colorProvider = { context ->
                XaulinXsThemedIconColors.getColorsIfAvailable(context)
                    ?: com.android.launcher3.icons.mono.ThemedIconDelegate.getColors(context)
            },
        )

    override fun createController(themeId: String): IconThemeController? =
        if (themeId == MONO_THEME_CONTROLLER.themeID) MONO_THEME_CONTROLLER else null

    override fun logThemeEvent(themeId: String, logger: StatsLogger) {
        logger.log(LAUNCHER_THEMED_ICON_ENABLED)
    }
}
