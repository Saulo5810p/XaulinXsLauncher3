#!/usr/bin/env python3
"""
fix_misc_toggles_persistence.py  --  rode na RAIZ do repositorio XaulinXsLauncher3.

BUG
    Em R'Home 3 > R's Misc, os interruptores "Pagina de musica" e
    "Sua Ideia... (voz)" nao desativavam; so o clima funcionava.

CAUSA RAIZ (confirmada lendo o codigo)
    MiscToggles.kt gravava a preferencia com LauncherPrefs.put(...), que
    internamente usa SharedPreferences.Editor.apply() -- gravacao em DISCO
    ASSINCRONA. Logo em seguida chamava XaulinXsAppRestarter.restart(), que
    termina com Process.killProcess(). O processo morria antes do disco ser
    escrito; o launcher reabria lendo o valor antigo (true) e recriava as
    paginas (Workspace.xaulinXsInsertMusicPageIfEnabled / ...IdeaPage...).
    O clima funciona porque NAO reinicia o app (nao ha kill no meio).
    O logcat confirma: nas duas aberturas do launcher as views
    XaulinXsMusicPageView e XaulinXsIdeaPageView sao adicionadas de novo.

CORRECAO
    1) Music e Idea passam a gravar com LauncherPrefs.putSync(...) (commit()
       sincrono) antes do restart.
    2) Ao ATIVAR a musica, remove o pedido de permissao disparado logo antes
       do restart: o processo morria 300 ms depois e o dialogo sumia. A
       propria lista de musica (XaulinXsMusicListWidget) ja pede a permissao
       de audio quando necessario.

Idempotente: pode rodar mais de uma vez; so altera o que ainda falta.
"""
import pathlib
import sys

TARGET = pathlib.Path(
    "modules/customizations/src/com/xaulinxs/customizations/settings/MiscToggles.kt"
)

# (descricao, trecho antigo, trecho novo)
EDITS = [
    (
        "Musica: gravar com putSync e nao pedir permissao antes do restart",
        """            val enabled = newValue as Boolean
            LauncherPrefs.get(context).put(XaulinXsMiscSettings.MUSIC_PAGE_ENABLED, enabled)
            if (enabled) {
                XaulinXsMiscPermissionActivity.request(context, XaulinXsMiscPermissions.AUDIO)
            }
            (context as? Activity)?.let { XaulinXsAppRestarter.restart(it) }
            true""",
        """            val enabled = newValue as Boolean
            // putSync (commit): o app e morto logo abaixo por XaulinXsAppRestarter.restart();
            // com put() (apply, assincrono) o valor nao chegava ao disco e a pagina voltava.
            // A permissao de audio e pedida pela propria lista de musica apos o restart.
            LauncherPrefs.get(context)
                .putSync(XaulinXsMiscSettings.MUSIC_PAGE_ENABLED.to(enabled))
            (context as? Activity)?.let { XaulinXsAppRestarter.restart(it) }
            true""",
    ),
    (
        "Idea (voz): gravar com putSync antes do restart",
        """            LauncherPrefs.get(context).put(XaulinXsMiscSettings.IDEA_PAGE_ENABLED, enabled)
            (context as? Activity)?.let { XaulinXsAppRestarter.restart(it) }""",
        """            // putSync (commit): o app e morto logo abaixo; com put() (apply) a gravacao se perdia.
            LauncherPrefs.get(context)
                .putSync(XaulinXsMiscSettings.IDEA_PAGE_ENABLED.to(enabled))
            (context as? Activity)?.let { XaulinXsAppRestarter.restart(it) }""",
    ),
]


def main() -> int:
    if not TARGET.is_file():
        print(f"ERRO: {TARGET} nao encontrado. Rode este script na raiz do repo.")
        return 1

    text = TARGET.read_text(encoding="utf-8")
    original = text
    changed = 0

    for desc, old, new in EDITS:
        if new in text:
            print(f"[ja aplicado] {desc}")
            continue
        if old not in text:
            print(f"ERRO: trecho esperado nao encontrado ({desc}).")
            print("      O arquivo foi alterado manualmente? Nada foi gravado.")
            return 2
        text = text.replace(old, new, 1)
        changed += 1
        print(f"[ok] {desc}")

    # Sanidade: nenhuma gravacao assincrona restante antes de restart.
    for flag in ("MUSIC_PAGE_ENABLED", "IDEA_PAGE_ENABLED"):
        if f".put(XaulinXsMiscSettings.{flag}" in text:
            print(f"ERRO: ainda existe put() assincrono para {flag}.")
            return 3

    if changed:
        TARGET.write_text(text, encoding="utf-8")
        print(f"\n{changed} alteracao(oes) gravada(s) em {TARGET}.")
    elif text == original:
        print("\nNada a fazer: correcao ja estava aplicada.")

    print("Agora recompile (ex.: ./gradlew assembleNoQuickstepDebug) e teste os toggles.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
