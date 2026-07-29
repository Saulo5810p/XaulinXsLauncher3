from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")

p = Path("AndroidManifest.xml")
content = p.read_text(encoding="utf-8")

if "<queries>" in content:
    skip("bloco <queries> já existe")
else:
    anchor = "    <application\n"
    block = (
        "    <queries>\n"
        "        <intent>\n"
        "            <action android:name=\"android.intent.action.MAIN\" />\n"
        "            <category android:name=\"android.intent.category.LAUNCHER\" />\n"
        "        </intent>\n"
        "        <intent>\n"
        "            <action android:name=\"android.appwidget.action.APPWIDGET_PICK\" />\n"
        "        </intent>\n"
        "        <intent>\n"
        "            <action android:name=\"android.intent.action.APPLICATION_PREFERENCES\" />\n"
        "        </intent>\n"
        "        <provider android:authorities=\"com.android.launcher3.settings\" />\n"
        "    </queries>\n\n"
    )
    content = content.replace(anchor, block + anchor, 1)
    p.write_text(content, encoding="utf-8")
    ok("bloco <queries> adicionado")
