from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

p = Path("AndroidManifest.xml")
content = p.read_text(encoding="utf-8")

if "com.android.launcher3.notification.NotificationListener" in content:
    skip("NotificationListener já declarado")
else:
    anchor = '        <service\n            android:name="androidx.appfunctions.service.ExtensionAppFunctionService"'
    if anchor not in content:
        fail("não achei o ponto de ancoragem")
        raise SystemExit(1)
    block = (
        '        <service\n'
        '            android:name="com.android.launcher3.notification.NotificationListener"\n'
        '            android:label="@string/derived_app_name"\n'
        '            android:permission="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE"\n'
        '            android:exported="true">\n'
        '            <intent-filter>\n'
        '                <action android:name="android.service.notification.NotificationListenerService" />\n'
        '            </intent-filter>\n'
        '        </service>\n\n'
    )
    content = content.replace(anchor, block + anchor, 1)
    p.write_text(content, encoding="utf-8")
    ok("NotificationListener declarado")
