#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: crash FATAL EXCEPTION main -- ClassCastException:
XaulinXsThemedContextWrapper cannot be cast to android.app.ContextImpl
em SessionCommitReceiver (e qualquer outro BroadcastReceiver do
Manifest), alem do tema nunca aparecer aplicado em lugar nenhum.

Causa raiz: LauncherApplication.attachBaseContext() envolvia o Context
da Application INTEIRA com XaulinXsThemedContextWrapper, pra
interceptar materialColorX. Mas o Android instancia BroadcastReceiver
via ActivityThread.handleReceiver() fazendo cast interno do Context
para ContextImpl -- um cast que so funciona com o Context puro do
framework, nao com um ContextWrapper por cima dele. Isso derrubava
SessionCommitReceiver (registrado no Manifest, disparado a qualquer
momento por PackageInstaller) com o processo inteiro crashando antes
da UI conseguir renderizar de forma estavel -- por isso "o tema nao
aplicou em lugar nenhum": o app ficava preso num loop de crash antes
de a paleta calculada aparecer em qualquer tela.

Fix: remove o wrapper de LauncherApplication.attachBaseContext
completamente (o metodo inteiro). A interceptacao de cor continua
funcionando normalmente porque ja estava tambem instalada nas 3
Activities (Launcher, SettingsActivity, CustomColorsActivity), que sao
o unico lugar onde a UI de fato eh inflada -- BroadcastReceiver nunca
precisou dela.

Rode este script na RAIZ do checkout local do repo (mesmo diretorio do
gradlew), dentro do Termux.

python3 fix_receiver_crash.py

Idempotente.
"""
import sys
from pathlib import Path

def die(msg):
    print("ERRO:", msg)
    sys.exit(1)

if not Path("gradlew").exists():
    die("rode este script na raiz do checkout (onde esta o gradlew).")

PATCHES = [
    ('src/com/android/launcher3/LauncherApplication.java', 'import android.app.Application;\nimport android.content.Context;\nimport com.android.launcher3.dagger.DaggerLauncherAppComponent;\nimport com.android.launcher3.dagger.LauncherAppComponent;\nimport com.android.launcher3.dagger.LauncherBaseAppComponent;\nimport com.android.launcher3.dagger.LauncherComponentProvider;\nimport com.android.launcher3.util.TraceHelper;\nimport com.xaulinxs.customizations.theme.XaulinXsThemeColorResources;\nimport com.xaulinxs.customizations.theme.XaulinXsThemedContextWrapper;\n\npublic class LauncherApplication extends Application {\n\n    private volatile LauncherBaseAppComponent mAppComponent;\n\n    // XaulinXs Customizations — "UI-UX Custom Colors": envolve o Context\n    // base do processo com um wrapper que intercepta @color/materialColorX\n    // (ver XaulinXsThemeColorResources.kt para o porquê disso, em vez de\n    // tentar reescrever o XML empacotado no APK). Precisa ser attachBaseContext,\n    // não onCreate: getResources() já é chamado antes de onCreate rodar.\n    @Override\n    protected void attachBaseContext(Context base) {\n        super.attachBaseContext(new XaulinXsThemedContextWrapper(base));\n    }\n\n    @Override\n    public void onCreate() {\n        super.onCreate();\n        XaulinXsThemeColorResources.installIfEnabled(this);\n        LauncherComponentProvider.get(this).getMainProcessInitializer().init(this);\n    }', 'import android.app.Application;\nimport com.android.launcher3.dagger.DaggerLauncherAppComponent;\nimport com.android.launcher3.dagger.LauncherAppComponent;\nimport com.android.launcher3.dagger.LauncherBaseAppComponent;\nimport com.android.launcher3.dagger.LauncherComponentProvider;\nimport com.android.launcher3.util.TraceHelper;\nimport com.xaulinxs.customizations.theme.XaulinXsThemeColorResources;\n\npublic class LauncherApplication extends Application {\n\n    private volatile LauncherBaseAppComponent mAppComponent;\n\n    // XaulinXs Customizations — "UI-UX Custom Colors": NÃO envolver o\n    // Context da Application inteira aqui (attachBaseContext). Isso já\n    // foi tentado e causou crash real em produção: o framework Android\n    // faz cast interno de Context para ContextImpl em vários pontos que\n    // não passam pela Activity — por exemplo BroadcastReceiver\n    // (ActivityThread.handleReceiver) — e um ContextWrapper substituindo\n    // o Context "base" do processo inteiro quebra esse cast\n    // (ClassCastException: XaulinXsThemedContextWrapper cannot be cast\n    // to ContextImpl), derrubando SessionCommitReceiver e qualquer outro\n    // receiver/service que dependa do Context puro da Application. A\n    // interceptação de cor fica só nas Activities (Launcher,\n    // SettingsActivity, CustomColorsActivity), que é onde a UI é\n    // realmente inflada — ver XaulinXsThemeColorResources.kt.\n    @Override\n    public void onCreate() {\n        super.onCreate();\n        XaulinXsThemeColorResources.installIfEnabled(this);\n        LauncherComponentProvider.get(this).getMainProcessInitializer().init(this);\n    }'),
    ('src/com/android/launcher3/Launcher.java', '        // inflação). O wrapper de Application (LauncherApplication) cobre\n        // getApplicationContext(), mas Activity.getResources() usa o\n        // Resources da própria Activity, que NÃO herda do wrapper da\n        // Application — por isso precisa ser instalado de novo aqui. Ver\n        // XaulinXsThemeColorResources.kt para detalhes.', '        // inflação). Instalado SÓ aqui, na Activity — não em\n        // LauncherApplication.attachBaseContext: essa outra tentativa\n        // quebrou BroadcastReceiver (SessionCommitReceiver), porque o\n        // framework faz cast do Context de Application para ContextImpl\n        // em pontos internos que não passam pela Activity. Ver\n        // XaulinXsThemeColorResources.kt e o comentário em\n        // LauncherApplication.java para detalhes.'),
    ('src/com/android/launcher3/settings/SettingsActivity.java', '        // documentado em Launcher.attachBaseContext: o Resources desta\n        // Activity não herda do wrapper instalado em LauncherApplication,\n        // então precisa ser instalado de novo aqui para que a tela de\n        // Configurações (e a própria CustomColorsActivity) já reflita a\n        // paleta customizada.', '        // documentado em Launcher.attachBaseContext: instalado só nesta\n        // Activity (não em LauncherApplication), porque envolver o\n        // Context da Application inteira quebrou BroadcastReceiver\n        // (ver comentário em LauncherApplication.java).'),
    ('modules/customizations/src/com/xaulinxs/customizations/theme/XaulinXsThemeColorResources.kt', '    /** Chamado uma vez em LauncherApplication.attachBaseContext, antes de qualquer inflação. */', '    /** Chamado uma vez em LauncherApplication.onCreate(), populando o mapa de override cedo. */'),

]

patched, skipped = [], []
for rel_path, old, new in PATCHES:
    target = Path(rel_path)
    if not target.exists():
        die(f"nao encontrei {rel_path}. O repo mudou de estrutura?")
    content = target.read_text(encoding="utf-8")

    if new in content:
        skipped.append(rel_path)
        continue

    if old not in content:
        die(
            f"nao encontrei o bloco esperado em {rel_path}.\n"
            "O arquivo pode ja ter sido editado manualmente de outro jeito. "
            "Abortando sem mexer em nada -- me manda o conteudo atual do "
            "arquivo que eu ajusto o patch."
        )

    content = content.replace(old, new)
    target.write_text(content, encoding="utf-8")
    patched.append(rel_path)

print()
if patched:
    print("Arquivos corrigidos:")
    for p in patched:
        print("  ~", p)
if skipped:
    print("Ja corrigidos (pulados):")
    for p in skipped:
        print("  =", p)

if not patched:
    print()
    print("Ja aplicado -- nada a fazer.")
else:
    print()
    print("OK: crash do BroadcastReceiver corrigido.")
    print("Agora: git add -A && git commit -m \'fix: remove Application Context wrapper (quebrava BroadcastReceiver)\' && git push")
    print("Depois: ./gradlew assembleNoQuickstepDebug")
