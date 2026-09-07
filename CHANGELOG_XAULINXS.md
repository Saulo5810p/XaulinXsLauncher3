# R's Home3 (ex-XaulinXsLauncher3) — changelog consolidado

Este zip é o repositório **completo**, com todas as mudanças descritas
abaixo já aplicadas diretamente nos arquivos (não é um conjunto de
patches — é a árvore final, pronta pra compilar e/ou revisar).

Repositório original: https://github.com/Saulo5810p/XaulinXsLauncher3

## 1. Reorganização das "XaulinXs Customizations" → "R's Home3"

A tela única e desorganizada virou "R's Home3" (subtítulo "Make your idea
your own"), dividida em categorias:

- **Interface**: fonte customizada, Tamanho da grade
- **Ícone**: labels, tamanho, cores temáticas, transparência, cor manual,
  remover fundo/sombra dos ícones antigos
- **Menu de aplicativo**: véu temático, opacidade, transparência
- **Balões**: blur, cor customizada (segue o wallpaper por padrão)
- **Área de trabalho**: giroscópio, trocar wallpaper, desfoque
- **Barra de busca**: configuração da QSB
- **Widget**: blur
- **Pastas**: cor, transparência, tamanho

Nenhuma key de preferência foi renomeada — navegação usa a infraestrutura
que já existia em `SettingsActivity`.

## 2. Correções de bugs

- **Fonte customizada em widgets que se desaplicava sozinha**: agora
  reaplica a cada passada de layout (cobre listas/atualizações parciais
  de RemoteViews), não só quando o host recebe um `updateAppWidget()`
  inteiro. Ver `XaulinXsWidgetFontForcer.kt`.
- **Ícones temáticos que não aplicavam em alguns apps**: a flag
  `Flags.forceMonochromeAppIcons()` estava presa em `false` no stub
  manual de flags do projeto — apps sem layer `<monochrome>` própria
  nunca recebiam cor nenhuma. Ligada em `Flags.java`.
- **`default_wallpaper.png` não carregava**: nome do asset errado
  (`identidade_wallpaper.png` vs o real `default_wallpaper.png`) — mas
  essa correção foi substituída por uma solução mais completa, ver
  item 4 abaixo.
- **Balões brancos**: a cor deles dependia do dynamic color (Monet) do
  Android, cujo fallback estático é literalmente branco. Corrigido pra
  seguir a cor extraída do wallpaper por padrão (ver item 5).

## 3. Features novas

- **Remover fundo/sombra dos ícones antigos** (categoria Ícone):
  apps sem ícone adaptativo recebiam um `ColorDrawable` branco sintético
  + sombra; toggle novo remove os dois só pra esses ícones legados. Ver
  `BaseIconFactory.kt` / `XaulinXsLegacyIconAppearance.kt`.
- **Cor customizada dos balões** (3 sliders RGB + hex), com prioridade
  sobre a cor extraída do wallpaper quando ligada.
- **Tamanho da grade, 2x2 até 10x10** (categoria Interface — afeta Menu
  de aplicativo e Área de trabalho juntos, já que `numAllAppsColumns`
  usa `numColumns` como padrão quando não declarado). 17 grades novas em
  `res/xml/device_profiles.xml`, cada uma com banco de dados e layout
  padrão (vazio) próprios. Tamanhos de ícone/texto estimados
  proporcionalmente — não testados visualmente num aparelho real.
- **Cor/transparência/tamanho de pastas** (categoria Pastas), tudo
  neutro por padrão. Ver `XaulinXsFolderAppearance.kt` /
  `PreviewBackground.java`.
- **Desfoque da tela inicial** (categoria Área de trabalho, slider
  0-100%): usa `View.setRenderEffect` (Android 12+), rodando dentro da
  nossa própria janela — sem depender de cross-window blur do sistema
  (que já está documentado como bloqueado neste aparelho/ROM).

## 4. Wallpaper próprio do launcher (arquitetura nova)

O R's Home3 guarda seu próprio wallpaper em armazenamento **privado**
(`XaulinXsInAppWallpaper.kt`), desenhado por `XaulinXsWallpaperView`
(inserida no fundo de tudo em `launcher.xml`) — nunca mexe no wallpaper
real do sistema, EXCETO quando o usuário troca de wallpaper diretamente
por dentro do launcher (nova opção "Trocar wallpaper", categoria Área de
trabalho) — nesse caso os dois (nosso e o do sistema) são atualizados
juntos.

**Trade-offs aceitos:** sem parallax de rolagem, sem suporte a live
wallpaper como fundo do launcher.

## 5. Pipeline de cor unificado

`WallpaperColorHints.kt` (fonte única de cor pra ícones temáticos, véu do
menu de apps, cor dos balões e tema claro/escuro do sistema) agora
calcula a cor a partir do NOSSO wallpaper (via `WallpaperColors.
fromBitmap()`), com o wallpaper real do sistema só como recuo até o
nosso carregar. Mudança concentrada num único arquivo, efeito em cascata
em todo o resto.

## 6. Identidade do app

- **Nome do pacote (`applicationId`)**: `com.android.launcher3` →
  `r.home3`, em `build.gradle`. O `namespace` interno (pacote
  Java/Kotlin de todas as classes) continua `com.android.launcher3` —
  troca de propósito, ver explicação detalhada nos comentários do
  `build.gradle` e no chat. Corrigidos os pontos que dependiam do
  `applicationId` bater com uma string literal: os `targetPackage` dos
  `<intent>` das nossas Preferences, e uma checagem em
  `XaulinXsGlobalFontInflaterFactory.kt` que faria a fonte customizada
  parar de funcionar silenciosamente se não fosse corrigida.
  Deixado de propósito sem mudar: `ClockDrawableWrapper.kt`
  (`LAUNCHER_PACKAGE`), que é um protocolo público usado por apps de
  relógio animado de terceiros, não uma autochecagem.
- **Nome do app (`app_name`)**: "Launcher3" → "R's Home3" em TODOS os
  `res/values*/strings.xml` (quase 90 arquivos de idioma, incluindo os
  que tinham traduzido tipo "Tela de início 3" no português).

## 7. Removida: "UI-UX Custom Colors"

Feature descontinuada por pedido do usuário — ela nunca funcionou de
verdade (dependia de interceptar `Resources.getColor()`/
`getColorStateList()`, mas os métodos mais usados na prática,
`Context.getColor()`/`getColorStateList()`, são `final` e não dá pra
sobrescrever; cobertura completa exigiria Runtime Resource Overlay via
`aapt2`, inviável sem root no Termux). Removida por completo: Activity,
interceptação de Resources, gerador de paleta, e todas as referências em
`Launcher.java`, `SettingsActivity.java`, `LauncherApplication.java`,
Manifest e strings.

## Pendências conhecidas (não implementadas, por decisão do usuário)

- **Preview de wallpaper** nos balões/menu de apps/configurações — o
  usuário mencionou que é novidade do Launcher3 a partir do Android 17;
  investigado sem achado conclusivo (o repositório tem uma pasta
  vendorizada `android-17.0.0_r1-iconloaderlib`, mas é só da lib de
  ícones, não do Launcher3 principal). Deixado de lado por decisão do
  usuário.
- Editor de formato de ícone customizado (drawable redesenhável) — citado
  no pedido original, não chegou a ser abordado nesta rodada.
- Forçar aplicação de cores temáticas "em todos os ícones" — a correção
  da flag (item 2) resolve a causa raiz da maioria dos casos, mas não foi
  testada em todos os apps possíveis.
