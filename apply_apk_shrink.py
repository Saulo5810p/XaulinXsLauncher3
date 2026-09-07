#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XaulinXs Customizations — script de redução de tamanho do APK.

Aplica 3 mudanças (rode a partir da RAIZ do checkout):

  1) Remove androidx.cardview:cardview:1.0.0 — dependência com ZERO uso
     confirmado no código-fonte (nem Kotlin/Java, nem tag <CardView> em
     nenhum layout XML).

  2) Ativa minifyEnabled + shrinkResources nos buildTypes debug E release
     (o usuário builda sempre assembleNoQuickstepDebug, então o shrink
     precisa estar no debug também — antes não existia buildTypes
     nenhum, então não havia shrink em lugar algum). Isso deixa o R8
     remover automaticamente código não referenciado, incluindo os
     milhares de ícones não usados de material-icons-extended (são
     propriedades Kotlin comuns, não recursos — o shrink de código
     comum já cobre isso sozinho, sem precisar trocar nenhum import
     manualmente e arriscar quebrar o build).
     SourceFile/LineNumberTable são preservados nas regras extras para
     que crashes em logcat continuem apontando pro arquivo/linha reais
     mesmo com nomes de classe ofuscados.

  3) Cria proguard-xaulinxs.pro com as regras extras necessárias:
       - keep para protobuf-javalite (GeneratedMessageLite) — sem isso
         o app crasha em runtime com "Field X_ for Y not found", é um
         problema documentado oficialmente pelo próprio projeto
         protobuf, não uma suposição.
       - keepattributes SourceFile/LineNumberTable (ver acima).
     As regras do próprio Google (proguard.flags, já existente no repo
     mas até agora nunca referenciado em nenhum buildTypes) também
     passam a ser usadas.
     Deliberadamente NÃO adiciona regras -keep amplas para
     androidx.**/kotlin.**/etc — a maioria dessas libs já embute suas
     próprias consumer-rules.pro dentro do .aar, e regras amplas
     anulariam boa parte do ganho de shrink sem necessidade real.

NÃO mexe nas 4 ABIs nativas (arm64-v8a/armeabi-v7a/x86/x86_64) — isso
continua sendo uma escolha do usuário, fora do escopo deste script.

Idempotente: pode rodar várias vezes seguidas sem duplicar nada.

IMPORTANTE — teste obrigatório após rodar: minify/R8 é a mudança mais
arriscada feita neste projeto até agora. Regras erradas ou faltando
causam crash em RUNTIME (não erro de compilação) — o build vai compilar
limpo mesmo se algo quebrar. Teste o app REAL no aparelho depois de
buildar: abra o menu de apps, o menu de contexto (segurar o dedo num
ícone), redimensione um widget, abra o seletor de widgets, abra as
configurações do XaulinXs. Se algo crashar, mande o logcat.

Uso:
    python3 apply_apk_shrink.py
"""

import hashlib
import sys
from pathlib import Path

ROOT = Path.cwd()


def fail(msg: str) -> None:
    print(f"[ERRO] {msg}")
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def skip(msg: str) -> None:
    print(f"[SKIP] {msg}")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_new_file(rel_path: str, content: str) -> None:
    path = ROOT / rel_path
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if sha256(existing) == sha256(content):
            skip(f"{rel_path} (já existe, idêntico)")
            return
        fail(
            f"{rel_path} já existe com conteúdo DIFERENTE do esperado — "
            "não vou sobrescrever. Verifique manualmente antes de rodar de novo."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    ok(f"{rel_path} (criado)")


def patch_file(rel_path: str, marker: str, old: str, new: str, label: str) -> None:
    path = ROOT / rel_path
    if not path.exists():
        fail(f"{rel_path} não encontrado — checkout inesperado, abortando.")
    content = path.read_text(encoding="utf-8")
    if marker in content:
        skip(f"{label} (marcador já presente em {rel_path})")
        return
    count = content.count(old)
    if count == 0:
        fail(
            f"{label}: trecho esperado não encontrado em {rel_path}. "
            "O arquivo pode ter mudado desde que este script foi gerado — "
            "não vou aplicar um patch às cegas."
        )
    if count > 1:
        fail(
            f"{label}: trecho esperado aparece {count} vezes em {rel_path} "
            "(deveria ser único) — abortando."
        )
    path.write_text(content.replace(old, new, 1), encoding="utf-8")
    ok(f"{label} ({rel_path})")


PROGUARD_XAULINXS_PRO = '''# XaulinXs Customizations — regras R8/ProGuard extras.
#
# As regras do próprio Google para o Launcher3 (Fragment, RecyclerView
# a11y, proto nano, DiscoveryBounce por reflexão etc.) já vêm de
# proguard.flags, referenciado junto com este arquivo no build.gradle —
# não duplicar nada daqui.
#
# A maioria das libs do AndroidX/Compose/Dagger já embute suas próprias
# consumer-rules.pro dentro do próprio .aar, então NÃO adicionamos regras
# amplas tipo "-keep class androidx.** { *; }" aqui — isso anularia boa
# parte do ganho de shrink sem necessidade real. Só entram regras para
# casos confirmados de reflexão que o R8 não detecta sozinho.

# Preserva nomes de arquivo e números de linha nos stack traces mesmo com
# minify ativo — sem isso, um crash em logcat mostra só "at a.b.c.a(:1)"
# em vez do arquivo/linha reais, dificultando diagnóstico (usuário pediu
# minify ativo também no build Debug, que é o único que ele usa no
# dia a dia — precisamos continuar conseguindo ler stacktraces de crash
# real do jeito que já fizemos nos diagnósticos anteriores).
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile

# protobuf-javalite: a runtime "Lite" usa reflexão interna para acessar
# os campos gerados (evita gerar hashCode/equals/parse manualmente).
# Sem esta regra, R8 renomeia/obfusca esses campos e o app crasha em
# runtime com "Field X_ for Y not found" — bug documentado oficialmente
# pelo próprio projeto protobuf, não é speculação:
# https://github.com/protocolbuffers/protobuf/blob/main/java/lite.md
-keep class * extends com.google.protobuf.GeneratedMessageLite { *; }

# XaulinXs Customizations: nada aqui usa reflexão por nome de classe
# nem persiste dados via nome de classe/pacote (confirmado por varredura
# do código-fonte antes de ativar minify — todas as chaves de
# LauncherPrefs/SharedPreferences do módulo são strings literais fixas,
# não derivadas de simpleName/javaClass). Se algum crash aparecer no
# teste real mencionando uma classe com nome ofuscado (tipo "a.b.c"),
# é sinal de reflexão não coberta aqui — reportar a stacktrace para
# adicionar a regra específica que faltou.
'''


def apply_new_files() -> None:
    write_new_file("proguard-xaulinxs.pro", PROGUARD_XAULINXS_PRO)


def apply_remove_cardview() -> None:
    rel = "build.gradle"
    marker_absent = "androidx.cardview:cardview"
    path = ROOT / rel
    if not path.exists():
        fail(f"{rel} não encontrado — checkout inesperado, abortando.")
    content = path.read_text(encoding="utf-8")
    if marker_absent not in content:
        skip("remover androidx.cardview (já ausente de build.gradle)")
        return
    old = "    implementation 'androidx.cardview:cardview:1.0.0'\n"
    count = content.count(old)
    if count == 0:
        fail(
            "remover androidx.cardview: a linha esperada não bate "
            "exatamente (build.gradle pode ter mudado) — abortando."
        )
    if count > 1:
        fail("remover androidx.cardview: linha aparece mais de uma vez — abortando.")
    path.write_text(content.replace(old, "", 1), encoding="utf-8")
    ok("build.gradle: removida dependência androidx.cardview (zero uso confirmado)")


def apply_build_types() -> None:
    rel = "build.gradle"
    marker = "XaulinXs Customizations: redução real de tamanho do APK"

    old = '''    buildFeatures {
        buildConfig true
    }
}'''

    new = '''    buildFeatures {
        buildConfig true
    }

    buildTypes {
        debug {
            // XaulinXs Customizations: usuário pediu shrink também no
            // Debug (fluxo real de build é sempre assembleNoQuickstepDebug,
            // nunca Release). SourceFile/LineNumberTable ficam preservados
            // (ver proguard-xaulinxs.pro) para que um crash em logcat
            // continue apontando pro arquivo/linha certos mesmo com nomes
            // de classe ofuscados — mesmo método de diagnóstico já usado
            // nos crashes anteriores continua funcionando.
            minifyEnabled true
            shrinkResources true
            proguardFiles(
                getDefaultProguardFile('proguard-android-optimize.txt'),
                'proguard.flags',
                'proguard-xaulinxs.pro',
            )
        }
        release {
            // XaulinXs Customizations: redução real de tamanho do APK.
            // minifyEnabled ativa o R8 (remove classes/métodos/campos não
            // referenciados — inclusive os milhares de ícones não usados
            // de material-icons-extended, que é código Kotlin comum, não
            // recurso, então o shrink de CÓDIGO já cobre isso sozinho).
            // shrinkResources depende de minifyEnabled e remove
            // drawables/layouts/strings não referenciados.
            minifyEnabled true
            shrinkResources true
            proguardFiles(
                getDefaultProguardFile('proguard-android-optimize.txt'),
                'proguard.flags',
                'proguard-xaulinxs.pro',
            )
        }
    }
}'''

    patch_file(rel, marker, old, new, "build.gradle: buildTypes debug+release com shrink ativo")


def main() -> None:
    print(f"Aplicando patches em: {ROOT}\\n")

    if not (ROOT / "src" / "com" / "android" / "launcher3").exists():
        fail(
            "Não parece a raiz do checkout do XaulinXsLauncher3 "
            "(src/com/android/launcher3 não encontrado). Rode este script "
            "de dentro da pasta do repositório."
        )

    if not (ROOT / "proguard.flags").exists():
        fail(
            "proguard.flags não encontrado na raiz do checkout — esperado "
            "que já exista (regras do próprio Google). Checkout inesperado."
        )

    apply_new_files()
    print()
    apply_remove_cardview()
    apply_build_types()

    print()
    print("Aplicado:")
    print("  1) androidx.cardview removida (dependência morta, zero uso)")
    print("  2) minifyEnabled + shrinkResources ativos em debug E release")
    print("  3) proguard-xaulinxs.pro criado (regras extras: protobuf-javalite")
    print("     + preservação de SourceFile/LineNumberTable para logcat legível)")
    print()
    print("Build: ./gradlew assembleNoQuickstepDebug (igual sempre)")
    print()
    print("*** TESTE OBRIGATÓRIO NO APARELHO REAL DEPOIS DE INSTALAR: ***")
    print("  - abrir o menu de apps (blur/transparência)")
    print("  - segurar o dedo num ícone (menu de contexto)")
    print("  - redimensionar um widget")
    print("  - abrir o seletor de widgets")
    print("  - abrir XaulinXs Customizations e testar um interruptor")
    print("  Se algo crashar, mande o logcat para eu ajustar as regras.")


if __name__ == "__main__":
    main()
