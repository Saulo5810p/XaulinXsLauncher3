#!/usr/bin/env python3
"""
Ativa 3 feature flags reais do AOSP no stub aosp-stubs/com/android/launcher3/Flags.java:

1. expandableLongPressMenu  -> popup de long-press em ícone em Jetpack Compose
   (accordion com física de mola nativa na expansão/colapso), lado a lado com
   o header customizado XaulinXs (nome/ícone grande/switch esconder app), que
   continua intacto pois é injetado ANTES dessa decisão em
   PopupContainerWithArrow.create().

2. enableLauncherIconShapes  -> necessária junto com a flag 3 (AND lógico em
   Folder.getFolderAnimationManager()) para ativar a animação elástica real
   de abrir/fechar pasta. EFEITO COLATERAL: também sobe
   DatabaseHelper.SCHEMA_VERSION de 32 para 34, e muda formato/preview de
   ícones em PredictedAppIcon/ClipIconView/ClippedFolderIconLayoutRule.

3. enableExpressiveFolderExpansion  -> junto com a flag 2, troca
   FolderAnimationManager (antigo) por FolderAnimationSpringBuilderManager
   (física de mola de verdade) ao abrir/fechar pastas.

Uso:
    python3 apply_flags_compose_popup_and_folder_spring.py [caminho_do_repo]

Se caminho_do_repo não for passado, usa o diretório atual.
Idempotente: pode rodar várias vezes sem duplicar nem quebrar nada.
"""
import sys
from pathlib import Path

REPLACEMENTS = [
    (
        "expandableLongPressMenu",
        "    public static boolean expandableLongPressMenu() { return false; }",
        """    // XaulinXs Customizations: ativada pra testar o popup de long-press em
    // ícone redesenhado em Jetpack Compose (accordion, física de mola nativa
    // na expansão/colapso das seções) lado a lado com o header customizado
    // (nome/ícone grande/switch esconder app) já existente, que continua
    // sendo injetado antes disso em PopupContainerWithArrow.create() e não é
    // afetado por esta flag.
    public static boolean expandableLongPressMenu() { return true; }""",
    ),
    (
        "enableLauncherIconShapes",
        "    public static boolean enableLauncherIconShapes() { return false; }",
        """    // XaulinXs Customizations: ativada junto com enableExpressiveFolderExpansion
    // (mais abaixo) para ligar a animação elástica real de abrir/fechar pasta
    // (FolderAnimationSpringBuilderManager, física de mola). Efeito colateral
    // ciente e aceito: também sobe DatabaseHelper.SCHEMA_VERSION de 32 para 34
    // e muda formato/preview de ícones (PredictedAppIcon, ClipIconView,
    // ClippedFolderIconLayoutRule).
    public static boolean enableLauncherIconShapes() { return true; }""",
    ),
    (
        "enableExpressiveFolderExpansion",
        "    public static boolean enableExpressiveFolderExpansion() { return false; }",
        """    // XaulinXs Customizations: ativada junto com enableLauncherIconShapes
    // (acima) para ligar a animação elástica real de abrir/fechar pasta via
    // FolderAnimationSpringBuilderManager (física de mola de verdade), em vez
    // do FolderAnimationManager antigo.
    public static boolean enableExpressiveFolderExpansion() { return true; }""",
    ),
]


def main():
    repo_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    target = repo_root / "aosp-stubs" / "com" / "android" / "launcher3" / "Flags.java"

    if not target.exists():
        print(f"ERRO: arquivo não encontrado em {target}")
        print("Rode este script a partir da raiz do repo, ou passe o caminho como argumento.")
        sys.exit(1)

    content = target.read_text(encoding="utf-8")
    changed = False
    already_applied = []
    conflicts = []

    for name, old, new in REPLACEMENTS:
        if new in content:
            already_applied.append(name)
            continue
        if old not in content:
            conflicts.append(name)
            continue
        content = content.replace(old, new)
        changed = True
        print(f"Ativado: {name}")

    if conflicts:
        print()
        print("ERRO: não encontrei a linha original esperada para:")
        for name in conflicts:
            print(f"  - {name}")
        print("O arquivo pode já ter sido editado de outra forma. Nada foi salvo.")
        sys.exit(1)

    if changed:
        target.write_text(content, encoding="utf-8")
        print(f"\nArquivo salvo: {target}")

    if already_applied and not changed:
        print(f"OK (já aplicado, nada a fazer): {', '.join(already_applied)}")
    elif already_applied:
        print(f"(já estavam aplicadas, puladas): {', '.join(already_applied)}")

    sys.exit(0)


if __name__ == "__main__":
    main()
