# XaulinXs Customizations — regras R8/ProGuard extras.
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
