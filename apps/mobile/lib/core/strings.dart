import 'package:flutter/widgets.dart';

class AppStrings {
  const AppStrings(this.languageCode);

  final String languageCode;

  bool get isGerman => languageCode == 'de';

  static AppStrings of(BuildContext context) =>
      AppStrings(Localizations.localeOf(context).languageCode);

  String get appName => 'LadePulse DE';
  String get pulse => isGerman ? 'Deutschland-Puls' : 'Germany Pulse';
  String get liveMap => isGerman ? 'Live-Karte' : 'Live map';
  String get timeMachine =>
      isGerman ? 'Netz-Zeitmaschine' : 'Network Time Machine';
  String get synthetic => isGerman
      ? 'Deterministische Demodaten — keine Live-Ladedaten.'
      : 'Deterministic demonstration data — not live charging data.';
  String get available => isGerman ? 'Verfügbar' : 'Available';
  String get inUse => isGerman ? 'Belegt' : 'In use';
  String get offline => isGerman ? 'Außer Betrieb' : 'Out of service';
  String get stale => isGerman ? 'Veraltet / unbekannt' : 'Stale / unknown';
  String get liveCoverage =>
      isGerman ? 'Live-Datenabdeckung' : 'Live-data coverage';
  String get hpcAvailable => isGerman ? 'HPC verfügbar' : 'HPC available';
  String get utilization => isGerman ? 'Auslastung' : 'Utilization';
  String get normal => isGerman ? 'Normalwert' : 'Normal';
  String get incidents => isGerman ? 'Ernste Ausfälle' : 'Serious outages';
  String get recovered => isGerman ? 'Erholt (1 Std.)' : 'Recovered (1 h)';
  String get pressure =>
      isGerman ? 'Ladedruck-Index' : 'Charging Pressure Index';
  String get confidence => isGerman ? 'Konfidenz' : 'Confidence';
  String get insufficientConfidence => isGerman
      ? 'Zu geringe Datenkonfidenz für einen belastbaren Index.'
      : 'Data confidence is too low for a reliable index.';
  String get methodology =>
      isGerman ? 'Nachvollziehbare Komponenten' : 'Explainable components';
  String get alternativesGap =>
      isGerman ? 'Lücke bei Alternativen' : 'Alternatives gap';
  String get selectedTime => isGerman ? 'Gewählter Zeitpunkt' : 'Selected time';
  String get now => isGerman ? 'Jetzt' : 'Now';
  String get openMap =>
      isGerman ? 'Netz auf der Karte öffnen' : 'Open network map';
  String get filters => isGerman ? 'Filter' : 'Filters';
  String get freshOnly => isGerman ? 'Nur aktuell' : 'Fresh only';
  String get availableNow => isGerman ? 'Jetzt verfügbar' : 'Available now';
  String get allPower => isGerman ? 'Alle Leistungen' : 'All power';
  String get sites => isGerman ? 'Standorte' : 'sites';
  String get clusters => isGerman ? 'Cluster' : 'clusters';
  String get connectors => isGerman ? 'Anschlüsse' : 'connectors';
  String get station => isGerman ? 'Ladestandort' : 'Charging site';
  String get dataAge => isGerman ? 'Datenalter' : 'Data age';
  String get reliability => isGerman ? 'Zuverlässigkeit' : 'Reliability';
  String get uptime =>
      isGerman ? 'Zeitgewichtete Betriebszeit' : 'Time-weighted uptime';
  String get observable => isGerman ? 'Beobachtbare Zeit' : 'Observable time';
  String get outages => isGerman ? 'Ausfälle' : 'Outages';
  String get mttr =>
      isGerman ? 'Mittlere Erholungszeit' : 'Mean time to recovery';
  String get history => isGerman ? '24-Stunden-Verlauf' : '24-hour history';
  String get alternatives => isGerman
      ? 'Zuverlässige Alternativen in der Nähe'
      : 'Nearby reliable alternatives';
  String get straightLine => isGerman ? 'Luftlinie' : 'straight-line';
  String get source => isGerman ? 'Quelle und Lizenz' : 'Source and licence';
  String get retry => isGerman ? 'Erneut versuchen' : 'Retry';
  String get inventoryDenominator =>
      isGerman ? 'Inventar-Nenner' : 'Inventory denominator';
  String get reported => isGerman ? 'Gemeldet' : 'Reported';
  String get fresh => isGerman ? 'Aktuell' : 'Fresh';
  String dayWindow(int days) =>
      isGerman ? '$days-Tage-Fenster' : '$days-day window';
  String samples(int count) =>
      isGerman ? '$count Stichproben' : '$count samples';
  String get timeWeightedEvents =>
      isGerman ? 'zeitgewichtete Ereignisse' : 'time-weighted events';
  String get noData =>
      isGerman ? 'Keine Daten für diesen Zeitpunkt.' : 'No data for this time.';
  String get mapLegend => isGerman
      ? 'Größe: Anschlüsse · Farbe: Auslastung · Ring: Ausfallanteil · Deckkraft: Konfidenz'
      : 'Size: connectors · Fill: utilization · Ring: offline share · Opacity: confidence';
}

extension StringsContext on BuildContext {
  AppStrings get strings => AppStrings.of(this);
}
