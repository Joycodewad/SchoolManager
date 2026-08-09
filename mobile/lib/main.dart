import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:provider/provider.dart';

import 'core/theme.dart';
import 'screens/shared/app_shell.dart';
import 'screens/shared/login_screen.dart';
import 'state/session_state.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Les dates et les montants sont formatés en français ; sans ce chargement
  // `DateFormat('d MMMM', 'fr_FR')` lèverait une exception au premier usage.
  await initializeDateFormatting('fr_FR', null);
  runApp(const EkdSchoolApp());
}

class EkdSchoolApp extends StatelessWidget {
  const EkdSchoolApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => SessionState()..restore(),
      child: MaterialApp(
        title: 'EKD School Manager',
        debugShowCheckedModeBanner: false,
        theme: buildAppTheme(),
        locale: const Locale('fr'),
        supportedLocales: const [Locale('fr'), Locale('en')],
        localizationsDelegates: const [
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        home: const _Root(),
      ),
    );
  }
}

/// Aiguillage : écran de démarrage, connexion ou application.
class _Root extends StatelessWidget {
  const _Root();

  @override
  Widget build(BuildContext context) {
    final status = context.select<SessionState, SessionStatus>((s) => s.status);

    return switch (status) {
      SessionStatus.loading => const Scaffold(
          body: Center(child: CircularProgressIndicator()),
        ),
      SessionStatus.signedOut => const LoginScreen(),
      SessionStatus.signedIn => const AppShell(),
    };
  }
}
