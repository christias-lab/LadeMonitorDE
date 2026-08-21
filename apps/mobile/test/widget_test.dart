import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ladepulse_mobile/app.dart';
import 'package:ladepulse_mobile/core/theme.dart';
import 'package:ladepulse_mobile/data/api.dart';
import 'package:ladepulse_mobile/data/models.dart';
import 'package:ladepulse_mobile/data/providers.dart';
import 'package:ladepulse_mobile/features/station/station_detail_screen.dart';
import 'package:timezone/data/latest.dart' as timezone;

void main() {
  setUpAll(timezone.initializeTimeZones);

  testWidgets(
    'dashboard labels synthetic data and replays ten-minute buckets',
    (tester) async {
      tester.view.physicalSize = const Size(430, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final api = FakeLadePulseApi();

      await tester.pumpWidget(
        ProviderScope(
          overrides: [apiProvider.overrideWithValue(api)],
          child: const LadePulseApp(),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Germany Pulse'), findsOneWidget);
      expect(
        find.text('Deterministic demonstration data — not live charging data.'),
        findsOneWidget,
      );
      expect(find.text('Charging Pressure Index'), findsOneWidget);
      expect(find.text('Live-data coverage'), findsOneWidget);
      expect(find.text('Available'), findsWidgets);
      expect(api.pulseCalls, [FakeLadePulseApi.reference]);

      await tester.tap(find.text('DE'));
      await tester.pumpAndSettle();
      expect(find.text('Deutschland-Puls'), findsOneWidget);
      expect(
        find.text('Deterministische Demodaten — keine Live-Ladedaten.'),
        findsOneWidget,
      );

      await tester.scrollUntilVisible(
        find.byType(Slider),
        500,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.drag(find.byType(Slider), const Offset(220, 0));
      await tester.pumpAndSettle();

      expect(api.pulseCalls.length, greaterThan(1));
      expect(api.pulseCalls.last.isBefore(FakeLadePulseApi.reference), isTrue);
      final delta = FakeLadePulseApi.reference.difference(api.pulseCalls.last);
      expect(delta.inMinutes % 10, 0);
    },
  );

  testWidgets('station view shows connector provenance and reliability', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(430, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final api = FakeLadePulseApi();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [apiProvider.overrideWithValue(api)],
        child: MaterialApp(
          theme: buildCockpitTheme(),
          locale: const Locale('en'),
          home: StationDetailScreen(
            siteId: 'site-1',
            selectedAt: FakeLadePulseApi.reference,
            onToggleLocale: _noop,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Demo Berlin Hub'), findsOneWidget);
    expect(find.textContaining('300 kW'), findsOneWidget);
    expect(find.textContaining('€'), findsOneWidget);
    expect(find.text('Time-weighted uptime'), findsOneWidget);
    expect(find.text('24-hour history'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.text('Demo source'),
      350,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Demo source'), findsOneWidget);
    expect(find.text('SYNTHETIC-DEMO-1.0'), findsOneWidget);
  });
}

void _noop() {}

class FakeLadePulseApi implements LadePulseApi {
  static final reference = DateTime.utc(2026, 7, 29, 12);
  final pulseCalls = <DateTime>[];

  @override
  Future<Metadata> metadata() async => Metadata(
    product: 'LadePulse DE',
    tagline: 'Test',
    dataMode: 'synthetic_demo',
    syntheticNotice:
        'Deterministic demonstration data — not live charging data.',
    referenceTime: reference,
    mapStyleUrl: 'https://demotiles.maplibre.org/style.json',
  );

  @override
  Future<PulseSnapshot> pulse(DateTime at) async {
    pulseCalls.add(at);
    return PulseSnapshot(
      dataMode: 'synthetic_demo',
      syntheticNotice:
          'Deterministic demonstration data — not live charging data.',
      bucketStart: at,
      sourceObservedAt: at,
      available: 3072,
      inUse: 500,
      outOfService: 80,
      staleUnknown: 40,
      hpcAvailable: 1200,
      utilization: 0.14,
      normalUtilization: 0.19,
      coverage: const Coverage(
        inventoryConnectors: 3692,
        reportedConnectors: 3692,
        freshConnectors: 3652,
        liveCoverage: 0.989,
      ),
      pressure: const Pressure(
        utilization: 0.14,
        offlineShare: 0.02,
        deviation: 0,
        alternativesGap: 0.18,
        confidence: 0.96,
        rawPressure: 0.09,
        score: 12,
        sufficientConfidence: true,
        weights: {
          'utilization': 0.4,
          'offline_share': 0.25,
          'deviation': 0.2,
          'alternatives_gap': 0.15,
        },
      ),
      seriousIncidents: 4,
      recoveredLastHour: 7,
    );
  }

  @override
  Future<MapResponse> map(MapQuery query) async => MapResponse(
    dataMode: 'synthetic_demo',
    notice: 'Deterministic demonstration data — not live charging data.',
    requestedAt: query.at,
    clustered: true,
    truncated: false,
    features: const [],
  );

  @override
  Future<StationDetail> station(String siteId, DateTime at) async =>
      StationDetail(
        dataMode: 'synthetic_demo',
        notice: 'Deterministic demonstration data — not live charging data.',
        siteId: siteId,
        name: 'Demo Berlin Hub',
        address: 'Teststraße 1',
        bundesland: 'Berlin',
        operatorName: 'DemoCharge',
        requestedAt: at,
        connectors: [
          ConnectorStatus(
            externalId: 'connector-1',
            evseExternalId: 'DE*LPD*E1',
            connectorType: 'CCS',
            maxPowerKw: 300,
            currentType: 'DC',
            physicalState: 'available',
            effectiveState: 'available',
            sourceObservedAt: at,
            dataAgeSeconds: 30,
            priceEurPerKwh: 0.59,
          ),
        ],
        reliability: const ReliabilitySummary(
          windowDays: 7,
          uptime: 0.982,
          observableShare: 0.99,
          outageCount: 2,
          medianOutageMinutes: 20,
          mttrMinutes: 25,
          sampleSize: 1000,
        ),
        nearbyAlternatives: const [
          AlternativeSite(
            siteId: 'site-2',
            name: 'Demo Alternative',
            distanceKm: 4.2,
            maxPowerKw: 150,
            reliabilityScore: 97.2,
          ),
        ],
        sourceName: 'Demo source',
        publicationName: 'Demo dynamic publication',
        licenceCode: 'SYNTHETIC-DEMO-1.0',
        attribution: 'Generated, not live.',
      );

  @override
  Future<StationHistory> stationHistory(
    String siteId,
    DateTime from,
    DateTime to,
  ) async => StationHistory(
    bucketMinutes: 10,
    points: List.generate(
      145,
      (index) => HistoryPoint(
        bucketStart: from.add(Duration(minutes: index * 10)),
        states: const StateCounts(
          available: 4,
          inUse: 1,
          outOfService: 0,
          staleUnknown: 0,
        ),
        utilization: 0.2,
        observableConnectors: 5,
      ),
    ),
  );
}
