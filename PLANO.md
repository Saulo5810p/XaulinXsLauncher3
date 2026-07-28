# XaulinXs-Launcher3 (AOSP 17, sem Quickstep)

Mesma filosofia do [XaulinXs-LatinIME](https://github.com/Saulo5810p/XaulinXs-LatinIME):
pegar o componente do AOSP, tirar as dependências da árvore inteira e deixá-lo
compilável via Gradle + GitHub Actions, sem Android Studio e sem `repo sync`.

## Descoberta principal

O próprio `Android.bp` já define um alvo `android_app { name: "Launcher3" }`
que usa apenas:

- `launcher-src` → `src/**`
- `launcher-src_no_quickstep` → `src_no_quickstep/**`
- `Launcher3ResLib` → `res/`
- manifests: `AndroidManifest.xml` + `AndroidManifest-common.xml`

Ou seja, o Google já mantém uma variante sem Quickstep. Não precisamos
amputar nada na unha — só ignorar `quickstep/` desde o começo.

## Fases

1. **Compilar.** Nem pensar em API 21 ainda. `minSdk 28`, `targetSdk 36`.
   Objetivo: `assembleDebug` rodar até o fim, mesmo com milhares de erros.
2. **Remover APIs ocultas / `@hide`** (`InteractionJankMonitor`,
   `WindowManagerProxy`, `SystemUiProxy`, `TaskbarManager`, `RecentsModel`,
   etc.) e tudo que exija `platform_apis: true` ou `privileged: true`.
3. **Downgrade de API**, um degrau por vez: 28 → 26 → 24 → 23 → 21.
4. **Modernização** (branch separada `gradle-modernization`): Gradle 9.6,
   AGP 9.x, Kotlin mais recente — só depois do primeiro APK.

## O que falta resolver (bloqueios conhecidos)

`Launcher3ResLib` linka várias libs internas do AOSP que não existem no
Maven público — vão quebrar o build e precisam de stub/substituição na
Fase 2/3:

- `SystemUI-statsd`, `SystemUISharedLib`, `WindowManager-Shell-shared-AOSP`
- `//frameworks/libs/systemui:iconloader_base`, `:animationlib`,
  `:contextualeducationlib`, `:mechanics`, `:msdl`
- `com_android_launcher3_flags_lib`, `com_android_wm_shell_flags_lib`,
  `com_android_systemui_shared_flags_lib` (aconfig — flags do framework)
- `dynamiccolors`, `widget_picker_component`, `workspace-functions`
  (parte já deve vir de `modules/widgetpicker`, `modules/appfunctions`)

Essas são exatamente as "centenas de erros de dependência" esperadas na
Fase 1 — corrigir uma por vez, igual no LatinIME.

## Estrutura do módulo único

Este repo usa **um projeto Gradle só**, sem subpasta `app/`: o
`build.gradle` da raiz aplica `com.android.application` direto e os
`sourceSets` apontam pra `src/`, `src_no_quickstep/`, `res/` etc. — as
mesmas pastas que já vieram do AOSP, sem duplicar nada.
