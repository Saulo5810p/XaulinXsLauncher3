from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

p = Path("AndroidManifest.xml")
content = p.read_text(encoding="utf-8")

if "com.android.launcher3.settings.SettingsActivity" in content:
    skip("SettingsActivity já declarada")
else:
    anchor = '        <activity android:name="com.android.launcher3.widgetpicker.WidgetPickerActivity"'
    block = (
        '        <activity\n'
        '            android:name="com.android.launcher3.settings.SettingsActivity"\n'
        '            android:label="@string/settings_button_text"\n'
        '            android:theme="@style/AppTheme"\n'
        '            android:exported="true">\n'
        '            <intent-filter>\n'
        '                <action android:name="android.intent.action.APPLICATION_PREFERENCES" />\n'
        '                <category android:name="android.intent.category.DEFAULT" />\n'
        '            </intent-filter>\n'
        '        </activity>\n\n'
    )
    content = content.replace(anchor, block + anchor, 1)
    p.write_text(content, encoding="utf-8")
    ok("SettingsActivity declarada")
