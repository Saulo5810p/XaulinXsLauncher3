#!/usr/bin/env python3
"""
XaulinXsLauncher3 — fix do bug "fonte não muda ao importar" (causa raiz)
=========================================================================

Aplica o patch cirúrgico (2 arquivos: CustomFontPreference.kt e
SettingsActivity.java) direto no seu checkout LOCAL existente — não
clona nada, não mexe em mais nenhum arquivo.

O que o script faz, em ordem, parando na primeira falha:
  1. Confirma que está sendo rodado de dentro do repo (raiz do
     XaulinXsLauncher3 — checa se AndroidManifest.xml existe).
  2. Confere que a árvore de trabalho está limpa nos dois arquivos que
     o patch vai tocar (se você já tiver mudanças locais não commitadas
     neles, o script para e avisa, em vez de arriscar conflito).
  3. Confere que o patch bate 100% (git apply --check) ANTES de
     escrever qualquer coisa.
  4. Aplica de verdade.
  5. Mostra o diff aplicado para conferência.
  6. Compila com Gradle (assembleDebug).
  7. Só imprime "SUCESSO" se todas as etapas passarem.

Uso — de DENTRO da pasta do repo no Termux:
    cd ~/XaulinXsLauncher3   (ou onde estiver o seu checkout)
    python3 /caminho/para/apply_font_import_fix.py
"""
import subprocess
import sys
import os

PATCH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "fix_custom_font_import.patch")

TOUCHED_FILES = [
    "modules/customizations/src/com/xaulinxs/customizations/settings/CustomFontPreference.kt",
    "src/com/android/launcher3/settings/SettingsActivity.java",
]


def run(cmd, check=True):
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd, text=True)
    if check and result.returncode != 0:
        print(f"\n[FALHOU] comando retornou {result.returncode}: {' '.join(cmd)}")
        sys.exit(1)
    return result.returncode


def main():
    if not os.path.isfile(PATCH_FILE):
        print(f"[FALHOU] patch não encontrado em: {PATCH_FILE}")
        print("Coloque fix_custom_font_import.patch na mesma pasta deste script.")
        sys.exit(1)

    # 1. Confirma que estamos na raiz do repo certo.
    if not os.path.isfile("AndroidManifest.xml"):
        print("[FALHOU] AndroidManifest.xml não encontrado na pasta atual.")
        print("Rode este script de dentro da raiz do seu checkout do")
        print("XaulinXsLauncher3 (cd até lá primeiro).")
        sys.exit(1)

    # 2. Não pisar em mudanças locais não commitadas nos arquivos alvo.
    print("=== Checando se há mudanças locais não commitadas nos arquivos alvo ===")
    status = subprocess.run(
        ["git", "status", "--porcelain", "--"] + TOUCHED_FILES,
        text=True, capture_output=True,
    )
    if status.stdout.strip():
        print("[FALHOU] Você tem mudanças locais não commitadas nestes arquivos:")
        print(status.stdout)
        print("Faça commit ou stash delas antes de rodar o patch, para não")
        print("arriscar perder trabalho ou gerar conflito.")
        sys.exit(1)
    print("OK — nada pendente nos dois arquivos que o patch toca.")

    # 3. Confere se o patch bate ANTES de tocar em qualquer arquivo real.
    print("\n=== Conferindo se o patch bate no seu checkout (dry-run) ===")
    run(["git", "apply", "--check", PATCH_FILE])

    # 4. Aplica de verdade.
    print("\n=== Aplicando o patch ===")
    run(["git", "apply", PATCH_FILE])

    # 5. Diff linha a linha para conferência visual final.
    print("\n=== Diff aplicado (confira visualmente) ===")
    run(["git", "diff", "--stat", "--"] + TOUCHED_FILES)
    run(["git", "diff", "--"] + TOUCHED_FILES)

    # 6. Compila.
    print("\n=== Compilando (assembleDebug) ===")
    run(["chmod", "+x", "./gradlew"])
    run(["./gradlew", "assembleDebug", "--console=plain"])

    print("\n" + "=" * 60)
    print("SUCESSO — patch aplicado no seu checkout local e build compilou limpo.")
    print("Revise o diff acima, teste no aparelho e, se estiver tudo")
    print("certo, dê 'git push'.")
    print("=" * 60)


if __name__ == "__main__":
    main()
