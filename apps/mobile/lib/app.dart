import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:go_router/go_router.dart';

import 'core/theme.dart';
import 'features/dashboard/dashboard_screen.dart';
import 'features/map/map_screen.dart';
import 'features/station/station_detail_screen.dart';

class LadePulseApp extends StatefulWidget {
  const LadePulseApp({super.key});

  @override
  State<LadePulseApp> createState() => _LadePulseAppState();
}

class _LadePulseAppState extends State<LadePulseApp> {
  Locale? _locale;
  late final GoRouter _router;

  @override
  void initState() {
    super.initState();
    _router = GoRouter(
      routes: [
        GoRoute(
          path: '/',
          builder: (context, state) =>
              DashboardScreen(onToggleLocale: _toggleLocale),
        ),
        GoRoute(
          path: '/map',
          builder: (context, state) => LiveMapScreen(
            selectedAt: _parseTime(state.uri.queryParameters['at']),
            onToggleLocale: _toggleLocale,
          ),
        ),
        GoRoute(
          path: '/stations/:siteId',
          builder: (context, state) => StationDetailScreen(
            siteId: state.pathParameters['siteId']!,
            selectedAt: _parseTime(state.uri.queryParameters['at']),
            onToggleLocale: _toggleLocale,
          ),
        ),
      ],
    );
  }

  static DateTime _parseTime(String? value) => value == null
      ? DateTime.utc(2026, 7, 29, 12)
      : DateTime.parse(value).toUtc();

  void _toggleLocale() {
    final current =
        _locale?.languageCode ??
        WidgetsBinding.instance.platformDispatcher.locale.languageCode;
    setState(() => _locale = Locale(current == 'de' ? 'en' : 'de'));
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'LadePulse DE',
      debugShowCheckedModeBanner: false,
      theme: buildCockpitTheme(),
      locale: _locale,
      supportedLocales: const [Locale('de'), Locale('en')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      routerConfig: _router,
    );
  }
}
