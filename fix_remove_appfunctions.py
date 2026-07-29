from pathlib import Path
import shutil

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")

p = Path("build.gradle")
content = p.read_text(encoding="utf-8")
original = content

removals = [
    "                'modules/appfunctions/src',\n",
    "\n    implementation 'androidx.appfunctions:appfunctions:1.0.0-alpha10'\n"
    "    implementation 'androidx.appfunctions:appfunctions-service:1.0.0-alpha10'\n"
    "    ksp 'androidx.appfunctions:appfunctions-compiler:1.0.0-alpha10'\n",
]
for old in removals:
    if old in content:
        content = content.replace(old, "", 1)
        ok(f"removido do build.gradle")
    else:
        skip("já removido")

if content != original:
    p.write_text(content, encoding="utf-8")
    ok("build.gradle salvo")

p2 = Path("src/com/android/launcher3/dagger/LauncherAppModule.kt")
content2 = p2.read_text(encoding="utf-8")
old2 = "            WorkspaceFunctionsLauncherModule::class,\n"
if old2 in content2:
    content2 = content2.replace(old2, "", 1)
    p2.write_text(content2, encoding="utf-8")
    ok("WorkspaceFunctionsLauncherModule::class removido")
else:
    skip("já removido")

p3 = Path("AndroidManifest.xml")
content3 = p3.read_text(encoding="utf-8")
original3 = content3

block_property = (
    "        <!-- App Functions Metadata -->\n"
    "        <property\n"
    "            android:name=\"android.app.appfunctions.app_metadata\"\n"
    "            android:resource=\"@xml/app_metadata\" />\n\n"
)
if block_property in content3:
    content3 = content3.replace(block_property, "", 1)
    ok("property app_metadata removido")

block_service = (
    "        <service\n"
    "            android:name=\"androidx.appfunctions.service.ExtensionAppFunctionService\"\n"
    "            android:permission=\"android.permission.BIND_APP_FUNCTION_SERVICE\"\n"
    "            android:exported=\"true\">\n"
    "            <intent-filter>\n"
    "                <action android:name=\"android.app.appfunctions.AppFunctionService\" />\n"
    "            </intent-filter>\n"
    "        </service>\n\n"
)
if block_service in content3:
    content3 = content3.replace(block_service, "", 1)
    ok("service ExtensionAppFunctionService removido")

if content3 != original3:
    p3.write_text(content3, encoding="utf-8")
    ok("AndroidManifest.xml salvo")

wf_dir = Path("deferred-appfunctions-widgetpicker/workspacefunctions")
if wf_dir.exists():
    shutil.rmtree(wf_dir)
    ok(f"pasta removida: {wf_dir}")

wf_module_file = Path("deferred-appfunctions-widgetpicker/WorkspaceFunctionsLauncherModule.kt")
if wf_module_file.exists():
    wf_module_file.unlink()
    ok(f"arquivo removido: {wf_module_file}")
