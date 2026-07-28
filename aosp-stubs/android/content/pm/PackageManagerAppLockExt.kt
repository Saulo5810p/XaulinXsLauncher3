package android.content.pm

import android.app.PendingIntent

/**
 * Stub manual — getEnableAppLockIntentForPackage() é um método novo do
 * PackageManager (recurso de AppLock) que ainda não existe em SDK pública.
 */
fun PackageManager.getEnableAppLockIntentForPackage(
    packageName: String,
    enable: Boolean,
): PendingIntent? = null
