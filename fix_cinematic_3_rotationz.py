"""
XaulinXs Customizations — Correcao pontual da Feature 3/N: erro de
compilacao "Unresolved reference 'rotationZ'". View do Android nao expoe
uma propriedade rotationZ em Kotlin (so getRotation()/setRotation() para
o eixo Z) — rotationX e rotationY existem, mas o eixo Z e so "rotation".
Erro meu de API ao portar do RetroPlayer (Compose usa rotationZ mesmo).

Corrige as 3 ocorrencias em AllAppsIconEnterEffect.kt, trocando
icon.rotationZ por icon.rotation.

Idempotente: pode rodar de novo sem duplicar nada.

USO (Termux, na raiz do projeto, DEPOIS de ja ter rodado
feature_cinematic_3_allapps_open_close.py):
    python3 fix_cinematic_3_rotationz.py
"""
from pathlib import Path

TARGET = "src/com/xaulinxs/customizations/cinematic/AllAppsIconEnterEffect.kt"

path = Path(TARGET)
assert path.exists(), (
    f"arquivo nao encontrado: {TARGET} — rode feature_cinematic_3_allapps_open_close.py "
    "primeiro (este script so corrige um arquivo que ele ja deveria ter criado)."
)

content = path.read_text(encoding="utf-8")

if "icon.rotationZ" not in content and ".rotationZ" not in content:
    print(f"SKIP: {TARGET} nao tem mais 'rotationZ' — correcao ja aplicada ou nao necessaria.")
else:
    before = content
    content = content.replace("icon.rotationZ", "icon.rotation")
    content = content.replace(
        "RetroPlayer Compose (NowPlayingScreen.kt): rotationZ decrescendo de",
        "RetroPlayer Compose (NowPlayingScreen.kt): rotation (eixo Z) decrescendo de",
    )
    count = before.count("icon.rotationZ")
    path.write_text(content, encoding="utf-8")
    print(f"APLICADO: {count} ocorrencia(s) de icon.rotationZ corrigidas para icon.rotation em {TARGET}")

print("\nOK — correcao aplicada. Proximo passo: ./gradlew assembleNoQuickstepDebug")
