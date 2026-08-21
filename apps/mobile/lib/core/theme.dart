import 'package:flutter/material.dart';

abstract final class PulseColors {
  static const background = Color(0xFF07111D);
  static const surface = Color(0xFF0E1C2B);
  static const surfaceHigh = Color(0xFF16283A);
  static const grid = Color(0xFF294056);
  static const textMuted = Color(0xFFA9B7C5);

  // These remain distinguishable without relying on a red/green pairing.
  static const available = Color(0xFF36D6C0);
  static const inUse = Color(0xFFF6C85F);
  static const offline = Color(0xFFF05D8A);
  static const stale = Color(0xFF91A0AE);
  static const accent = Color(0xFF58A6FF);
}

ThemeData buildCockpitTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: PulseColors.accent,
    brightness: Brightness.dark,
    surface: PulseColors.surface,
  );
  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorScheme: scheme,
    scaffoldBackgroundColor: PulseColors.background,
    cardTheme: const CardThemeData(
      color: PulseColors.surface,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.all(Radius.circular(18)),
        side: BorderSide(color: PulseColors.grid),
      ),
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: PulseColors.background,
      surfaceTintColor: Colors.transparent,
      centerTitle: false,
    ),
    chipTheme: ChipThemeData(
      backgroundColor: PulseColors.surface,
      selectedColor: PulseColors.accent.withValues(alpha: 0.22),
      side: const BorderSide(color: PulseColors.grid),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    ),
    sliderTheme: const SliderThemeData(
      activeTrackColor: PulseColors.accent,
      thumbColor: PulseColors.accent,
      inactiveTrackColor: PulseColors.grid,
    ),
    progressIndicatorTheme: const ProgressIndicatorThemeData(
      color: PulseColors.available,
      linearTrackColor: PulseColors.grid,
    ),
  );
}

Color statusColor(String state) => switch (state) {
  'available' => PulseColors.available,
  'in_use' => PulseColors.inUse,
  'out_of_service' => PulseColors.offline,
  _ => PulseColors.stale,
};
