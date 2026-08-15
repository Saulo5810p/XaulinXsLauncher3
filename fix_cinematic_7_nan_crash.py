#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XaulinXs Customizations — CORREÇÃO de crash na Feature 7/N (coverflow 3D
no Workspace).

BUG: launcher crashava ao abrir (FATAL EXCEPTION, IllegalArgumentException
"Cannot set 'scaleX' to Float.NaN" em CinematicCoverFlowEffect.kt).

CAUSA RAIZ: Workspace.bindAndInitFirstWorkspaceScreen() chama
updatePageScrollValues() (e portanto CinematicCoverFlowEffect.applyToPage)
durante a primeiríssima inserção de tela, ANTES do primeiro
onMeasure/onLayout rodar. Nesse momento getMeasuredWidth() do Workspace
ainda é 0, então o getScrollProgress() NATIVO do PagedView (que já existia
no AOSP, usado só pra fade antes desta feature) calcula delta/totalDistance
com totalDistance = 0 — resultado NaN ou Infinity. `Float.coerceIn()` NÃO
filtra NaN (qualquer comparação com NaN retorna false, então passa direto
pelo clamp) e View.setScaleX()/setRotationY() lançam
IllegalArgumentException para qualquer valor não-finito — daí o crash
FATAL logo na abertura do launcher.

CORREÇÃO: duas guardas em CinematicCoverFlowEffect.kt — (1) se
scrollProgress recebido não for finito, a página é resetada ao estado
neutro (sem rotação/perspectiva) e a função retorna sem aplicar nada
quebrado; a próxima chamada real de scroll (já com layout medido) corrige
a transformação normalmente; (2) cameraDistance só é aplicado se a
density resolvida for finita e positiva, evitando um segundo ponto
potencial de valor inválido. Mais uma guarda defensiva equivalente em
GyroTiltProvider.kt (spring listeners só atualizam tiltX/tiltY se o valor
for finito) — não é a causa deste crash, mas fecha o mesmo tipo de risco
por segurança.

Este script assume que feature_cinematic_7_coverflow_3d_workspace.py já
foi rodado antes (detecta pelo marcador do arquivo). Se você ainda não
rodou a feature 7, rode o script original primeiro — este aqui só
corrige, não cria do zero.

Script idempotente — pode rodar várias vezes sem duplicar nada.

Uso:
    python3 fix_cinematic_7_nan_crash.py /caminho/do/repo
    (ou rode de dentro da raiz do repo sem argumento)
"""

import os
import sys

MARKER_COVERFLOW_FILE = "// XAULINXS_COVERFLOW_EFFECT_FILE"
MARKER_FIX_APPLIED = "// XAULINXS_NAN_CRASH_FIX_APPLIED"

COVERFLOW_FILE_PATH = "src/com/xaulinxs/customizations/cinematic/CinematicCoverFlowEffect.kt"
GYRO_FILE_PATH = "src/com/xaulinxs/customizations/cinematic/GyroTiltProvider.kt"


def find_repo_root(start):
    candidates = [start] + ([os.path.join(start, d) for d in os.listdir(start)] if os.path.isdir(start) else [])
    for c in candidates:
        if os.path.isfile(os.path.join(c, COVERFLOW_FILE_PATH)):
            return c
    return None


def fix_coverflow_file(repo_root):
    path = os.path.join(repo_root, COVERFLOW_FILE_PATH)
    if not os.path.isfile(path):
        print(
            f"[!] ERRO: {path} não encontrado. Rode "
            "feature_cinematic_7_coverflow_3d_workspace.py primeiro — "
            "este script só corrige uma feature já aplicada."
        )
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if MARKER_FIX_APPLIED in content:
        print("[=] CinematicCoverFlowEffect.kt já tem a correção do crash NaN — pulando.")
        return True

    if MARKER_COVERFLOW_FILE not in content:
        print(
            f"[!] ERRO: {path} não parece ser o arquivo esperado da feature 7 "
            "(marcador não encontrado). Abortando por segurança."
        )
        return False

    old_body = (
        "    @JvmStatic\n"
        "    fun applyToPage(page: View, scrollProgress: Float) {\n"
        "        val pageOffset = scrollProgress.coerceIn(-1.4f, 1.4f)\n"
        "        val absOffset = abs(pageOffset)\n"
        "\n"
        "        val rotationY = (pageOffset * ROTATION_MULTIPLIER)\n"
        "            .coerceIn(-ROTATION_MAX, ROTATION_MAX) + (GyroTiltProvider.tiltX * 0.55f)\n"
        "        val scale = (SCALE_BASE - (absOffset * SCALE_FALLOFF)).coerceIn(SCALE_MIN, SCALE_MAX)\n"
        "        val alpha = (1f - (absOffset * ALPHA_FALLOFF)).coerceIn(ALPHA_MIN, 1f)\n"
        "\n"
        "        page.cameraDistance = CAMERA_DISTANCE_DP * page.resources.displayMetrics.density\n"
        "        page.rotationY = rotationY\n"
        "        page.rotationX = GyroTiltProvider.tiltY * 0.35f\n"
        "        page.scaleX = scale\n"
        "        page.scaleY = scale\n"
        "        page.alpha = alpha\n"
        "    }\n"
    )
    new_body = (
        f"    {MARKER_FIX_APPLIED}\n"
        "    @JvmStatic\n"
        "    fun applyToPage(page: View, scrollProgress: Float) {\n"
        "        // Guarda contra NaN/Infinity: getScrollProgress() nativo do\n"
        "        // PagedView divide por totalDistance (largura medida da página\n"
        "        // vizinha), que ainda é 0 na primeíssima inserção de tela\n"
        "        // (Workspace.bindAndInitFirstWorkspaceScreen chama\n"
        "        // updatePageScrollValues() antes do primeiro onMeasure/onLayout\n"
        "        // rodar). 0/0 = NaN, delta/0 = Infinity — coerceIn NÃO filtra\n"
        "        // NaN (qualquer comparação com NaN é false, passa direto) e\n"
        "        // View.setScaleX/setRotationY lançam IllegalArgumentException\n"
        "        // pra qualquer valor não-finito. Sem isso o launcher crasha ao\n"
        "        // abrir. Resposta segura: página fica no estado neutro (sem\n"
        "        // rotação/perspectiva) até o layout estar medido de verdade —\n"
        "        // a próxima chamada real de scroll corrige a transformação.\n"
        "        if (!scrollProgress.isFinite()) {\n"
        "            resetPage(page)\n"
        "            return\n"
        "        }\n"
        "\n"
        "        val pageOffset = scrollProgress.coerceIn(-1.4f, 1.4f)\n"
        "        val absOffset = abs(pageOffset)\n"
        "\n"
        "        val rotationY = (pageOffset * ROTATION_MULTIPLIER)\n"
        "            .coerceIn(-ROTATION_MAX, ROTATION_MAX) + (GyroTiltProvider.tiltX * 0.55f)\n"
        "        val scale = (SCALE_BASE - (absOffset * SCALE_FALLOFF)).coerceIn(SCALE_MIN, SCALE_MAX)\n"
        "        val alpha = (1f - (absOffset * ALPHA_FALLOFF)).coerceIn(ALPHA_MIN, 1f)\n"
        "\n"
        "        // Segunda guarda: cameraDistance depende de resources/displayMetrics,\n"
        "        // que também pode devolver density 0 em contextos degenerados\n"
        "        // (ex.: view ainda não anexada). Se algo aqui não for finito,\n"
        "        // aplica só rotação/escala/alpha (já garantidos finitos acima) e\n"
        "        // pula a perspectiva em vez de arriscar outro crash.\n"
        "        val density = page.resources?.displayMetrics?.density ?: 0f\n"
        "        if (density.isFinite() && density > 0f) {\n"
        "            page.cameraDistance = CAMERA_DISTANCE_DP * density\n"
        "        }\n"
        "        page.rotationY = rotationY\n"
        "        page.rotationX = GyroTiltProvider.tiltY * 0.35f\n"
        "        page.scaleX = scale\n"
        "        page.scaleY = scale\n"
        "        page.alpha = alpha\n"
        "    }\n"
    )
    if old_body not in content:
        print(
            "[!] ERRO: corpo de applyToPage() não encontrado no formato esperado "
            "(arquivo foi editado manualmente?) — abortando por segurança."
        )
        return False
    content = content.replace(old_body, new_body, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] CinematicCoverFlowEffect.kt: guardas contra NaN/Infinity adicionadas")
    return True


def fix_gyro_file(repo_root):
    path = os.path.join(repo_root, GYRO_FILE_PATH)
    if not os.path.isfile(path):
        print(f"[!] AVISO: {path} não encontrado — pulando guarda extra do giroscópio (não crítico).")
        return True
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if "if (value.isFinite()) tiltX = value" in content:
        print("[=] GyroTiltProvider.kt já tem a guarda extra de NaN — pulando.")
        return True

    old_springs = (
        "    private val springX = SpringAnimation(FloatValueHolder(0f)).apply {\n"
        "        setSpring(SpringForce(0f).apply { stiffness = 200f; dampingRatio = 0.9f })\n"
        "        addUpdateListener { _, value, _ -> tiltX = value }\n"
        "    }\n"
        "    private val springY = SpringAnimation(FloatValueHolder(0f)).apply {\n"
        "        setSpring(SpringForce(0f).apply { stiffness = 200f; dampingRatio = 0.9f })\n"
        "        addUpdateListener { _, value, _ -> tiltY = value }\n"
        "    }\n"
    )
    new_springs = (
        "    private val springX = SpringAnimation(FloatValueHolder(0f)).apply {\n"
        "        setSpring(SpringForce(0f).apply { stiffness = 200f; dampingRatio = 0.9f })\n"
        "        addUpdateListener { _, value, _ -> if (value.isFinite()) tiltX = value }\n"
        "    }\n"
        "    private val springY = SpringAnimation(FloatValueHolder(0f)).apply {\n"
        "        setSpring(SpringForce(0f).apply { stiffness = 200f; dampingRatio = 0.9f })\n"
        "        addUpdateListener { _, value, _ -> if (value.isFinite()) tiltY = value }\n"
        "    }\n"
    )
    if old_springs not in content:
        print("[!] AVISO: corpo dos springs não encontrado no formato esperado — pulando guarda extra (não crítico).")
        return True
    content = content.replace(old_springs, new_springs, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] GyroTiltProvider.kt: guarda extra contra NaN adicionada (defesa em profundidade)")
    return True


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    repo_root = find_repo_root(start)
    if repo_root is None:
        print(
            "[!] ERRO: não encontrei a estrutura esperada do XaulinXsLauncher3 "
            f"(procurado a partir de: {start}).\n"
            "    Rode este script de dentro da raiz do repo clonado, ou passe o "
            "caminho como argumento:\n"
            "    python3 fix_cinematic_7_nan_crash.py /caminho/do/repo"
        )
        sys.exit(1)

    print(f"[i] Repo detectado em: {repo_root}\n")

    ok1 = fix_coverflow_file(repo_root)
    ok2 = fix_gyro_file(repo_root)

    print("")
    if ok1 and ok2:
        print("[OK] Correção aplicada com sucesso. Rode:")
        print("     ./gradlew :quickstep:assembleDebug")
    else:
        print("[FALHOU] A correção não foi aplicada — veja os erros [!] acima.")
        print("         Confira com 'git diff' antes de compilar.")
        sys.exit(2)


if __name__ == "__main__":
    main()
