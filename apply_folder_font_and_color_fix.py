#!/usr/bin/env python3
"""
apply_folder_font_and_color_fix.py

XaulinXsLauncher3 — corrige 2 bugs de Pastas:

1) Nome da pasta ignorando a fonte customizada importada.
   Causa: Folder.java forçava, na inflação, a fonte de sistema
   "google-sans-flex" por cima de qualquer typeface já aplicado
   (o XaulinXsGlobalFontInflaterFactory já aplicava a fonte
   customizada corretamente antes dessa linha rodar).
   Fix: remove a chamada que sobrescrevia o typeface.

2) Cor manual + transparência da pasta ignoradas ao ABRIR a pasta
   (fica preta, usando o fallback do tema).
   Causa: o ícone de pasta FECHADO já usava XaulinXsFolderAppearance
   corretamente (PreviewBackground.getBgColor()), mas a FOLHA aberta
   usa um GradientDrawable (mBackground) inflado uma única vez, no
   construtor, direto de ?attr/folderBackgroundColor — nunca passava
   pelo resolvedor de cor/transparência do usuário.
   Fix: aplica XaulinXsFolderAppearance.resolveBackgroundColor() em
   mBackground, reaplicado toda vez que a pasta é aberta (assim
   também reflete mudanças de configuração sem precisar reiniciar
   o app).

Uso:
    python3 apply_folder_font_and_color_fix.py [caminho_do_repo]

Se caminho_do_repo não for passado, usa o diretório atual.
Idempotente: pode rodar quantas vezes quiser, sem duplicar nada.
"""

import sys
from pathlib import Path

TARGET_FILE = "src/com/android/launcher3/folder/Folder.java"

# --- Marcadores de idempotência ---
MARK_METHOD = "applyXaulinXsFolderBackground"
MARK_OPEN_CALL = "applyXaulinXsFolderBackground();"
MARK_TYPEFACE_REMOVED = 'mFolderName.setTypeface(Typeface.create("google-sans-flex"'

# --- Patch 1: remove import não usado de Typeface ---
OLD_IMPORT = 'import android.graphics.Typeface;\n'

# --- Patch 2: remove a linha que forçava a fonte de sistema ---
OLD_FONT_BLOCK = (
    '        mFolderName = findViewById(R.id.folder_name);\n'
    '        mFolderName.setTypeface(Typeface.create("google-sans-flex", Typeface.NORMAL));\n'
    '        mFolderName.setTextSize(TypedValue.COMPLEX_UNIT_PX,\n'
)
NEW_FONT_BLOCK = (
    '        mFolderName = findViewById(R.id.folder_name);\n'
    '        // XaulinXs fix: o AOSP original forçava aqui a fonte de sistema\n'
    '        // "google-sans-flex" por cima de qualquer typeface já aplicado\n'
    '        // na inflação (via XaulinXsGlobalFontInflaterFactory), fazendo o\n'
    '        // nome da pasta sempre ignorar a fonte customizada importada\n'
    '        // pelo usuário. Removido: o EditText já sai da inflação com o\n'
    '        // typeface certo (customizado, se houver; padrão do tema, senão)\n'
    '        // e não precisa ser sobrescrito aqui.\n'
    '        mFolderName.setTextSize(TypedValue.COMPLEX_UNIT_PX,\n'
)

# --- Patch 3: novo método applyXaulinXsFolderBackground() ---
OLD_GETBACKGROUND = (
    '    @Override\n'
    '    public Drawable getBackground() {\n'
    '        return mBackground;\n'
    '    }\n'
)
NEW_GETBACKGROUND = (
    '    @Override\n'
    '    public Drawable getBackground() {\n'
    '        return mBackground;\n'
    '    }\n'
    '\n'
    '    /**\n'
    '     * XaulinXs Customizations: aplica a cor manual (se ligada) + a\n'
    '     * transparência configuradas pelo usuário ao fundo da pasta aberta,\n'
    '     * usando o mesmo resolvedor já usado pelo ícone de pasta fechado\n'
    '     * ({@link com.android.launcher3.folder.PreviewBackground#getBgColor()}).\n'
    '     * ?attr/folderBackgroundColor é passado como [baseColor] — mesmo\n'
    '     * comportamento neutro por padrão: cor customizada desligada = usa\n'
    '     * a cor de tema original sem mudança; transparência 100% = opaco.\n'
    '     */\n'
    '    private void applyXaulinXsFolderBackground() {\n'
    '        int themeColor = mBackground.getColor() != null\n'
    '                ? mBackground.getColor().getDefaultColor()\n'
    '                : 0;\n'
    '        int resolved = com.xaulinxs.customizations.folder.XaulinXsFolderAppearance\n'
    '                .resolveBackgroundColor(getContext(), themeColor);\n'
    '        mBackground.setColor(resolved);\n'
    '    }\n'
)

# --- Patch 4: chamar o novo método a cada abertura da pasta ---
OLD_ANIMATE_OPEN = (
    '        Folder openFolder = getOpen(mActivityContext);\n'
    '        closeOpenFolder(openFolder);\n'
    '\n'
    '        if (blurOnMoreSurfaces()) {\n'
)
NEW_ANIMATE_OPEN = (
    '        Folder openFolder = getOpen(mActivityContext);\n'
    '        closeOpenFolder(openFolder);\n'
    '\n'
    '        // XaulinXs fix: mBackground (o fundo da FOLHA aberta, distinto do\n'
    '        // ícone de pasta fechado na tela inicial, que já usava\n'
    '        // XaulinXsFolderAppearance corretamente via PreviewBackground)\n'
    '        // era inflado uma única vez no construtor direto de\n'
    '        // ?attr/folderBackgroundColor (tema), sem nunca passar pela cor\n'
    '        // manual/transparência configuradas pelo usuário — por isso\n'
    '        // sempre aparecia preto (fallback do tema) ao abrir a pasta,\n'
    '        // ignorando os sliders. Reaplicamos aqui, a cada abertura, para\n'
    '        // também refletir mudanças feitas na configuração desde a\n'
    '        // última vez que a pasta foi aberta, sem precisar de listener\n'
    '        // permanente.\n'
    '        applyXaulinXsFolderBackground();\n'
    '\n'
    '        if (blurOnMoreSurfaces()) {\n'
)


def fail(msg: str) -> None:
    print(f"[ERRO] {msg}")
    sys.exit(1)


def main() -> None:
    repo_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    target = repo_root / TARGET_FILE

    if not target.is_file():
        fail(f"Não encontrei {TARGET_FILE} em {repo_root}. "
             f"Rode este script dentro da raiz do repo, ou passe o caminho como argumento.")

    text = target.read_text(encoding="utf-8")
    original_text = text
    applied = []
    skipped = []

    # --- Idempotência: já aplicado? ---
    # (Cuidado: o comentário do próprio fix menciona "google-sans-flex"
    # como documentação, então não dá pra checar só a presença da
    # string — precisa checar a CHAMADA de código em si.)
    already_font = MARK_TYPEFACE_REMOVED not in text
    already_bg_method = MARK_METHOD in text
    already_bg_call = MARK_OPEN_CALL in text

    # Patch 1 + 2: remoção da fonte forçada (import + linha)
    if already_font:
        skipped.append("Fix da fonte da pasta (já aplicado)")
    else:
        if OLD_FONT_BLOCK not in text:
            fail(
                "Não encontrei o bloco esperado do setTypeface('google-sans-flex') em "
                f"{TARGET_FILE}. O arquivo pode já ter sido editado manualmente de forma "
                "diferente — abortando sem tocar em nada, pra não sobrescrever edição sua."
            )
        text = text.replace(OLD_FONT_BLOCK, NEW_FONT_BLOCK, 1)

        # Remove o import de Typeface só se ele não for mais usado em
        # nenhum outro lugar do arquivo após a remoção acima.
        if "Typeface" not in text.replace(OLD_IMPORT, ""):
            if OLD_IMPORT in text:
                text = text.replace(OLD_IMPORT, "", 1)
        applied.append("Fix da fonte da pasta (removido setTypeface forçado)")

    # Patch 3: novo método applyXaulinXsFolderBackground()
    if already_bg_method:
        skipped.append("Método applyXaulinXsFolderBackground() (já existe)")
    else:
        if OLD_GETBACKGROUND not in text:
            fail(
                f"Não encontrei o método getBackground() esperado em {TARGET_FILE} "
                "para inserir o novo método ao lado. Abortando sem tocar em nada."
            )
        text = text.replace(OLD_GETBACKGROUND, NEW_GETBACKGROUND, 1)
        applied.append("Método applyXaulinXsFolderBackground() adicionado")

    # Patch 4: chamada em animateOpen()
    if already_bg_call:
        skipped.append("Chamada de applyXaulinXsFolderBackground() em animateOpen() (já existe)")
    else:
        if OLD_ANIMATE_OPEN not in text:
            fail(
                "Não encontrei o bloco esperado de animateOpen() (Folder openFolder = "
                f"getOpen(...)) em {TARGET_FILE}. Abortando sem tocar em nada."
            )
        text = text.replace(OLD_ANIMATE_OPEN, NEW_ANIMATE_OPEN, 1)
        applied.append("Chamada de applyXaulinXsFolderBackground() adicionada em animateOpen()")

    if text == original_text:
        print("Nada para aplicar — os 2 fixes já estavam presentes neste arquivo.")
        for s in skipped:
            print(f"  [já aplicado] {s}")
        return

    target.write_text(text, encoding="utf-8")

    print(f"Arquivo atualizado: {TARGET_FILE}\n")
    if applied:
        print("Aplicado nesta rodada:")
        for a in applied:
            print(f"  [OK] {a}")
    if skipped:
        print("\nJá estava aplicado (pulado):")
        for s in skipped:
            print(f"  [skip] {s}")

    print(
        "\nPronto. Compile com:\n"
        "  ./gradlew assembleNoQuickstepDebug\n"
        "\nTeste sugerido:\n"
        "  1) Abrir uma pasta e conferir se o NOME da pasta usa a fonte customizada.\n"
        "  2) Em Configurações > cor manual da pasta: ligar, escolher uma cor não-preta\n"
        "     e ajustar a transparência para menos de 100%.\n"
        "  3) Abrir a pasta na tela inicial e confirmar que a folha aberta usa a MESMA\n"
        "     cor manual, com a transparência aplicada (não deve mais aparecer preta)."
    )


if __name__ == "__main__":
    main()
