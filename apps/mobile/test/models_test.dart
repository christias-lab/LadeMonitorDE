import 'package:flutter_test/flutter_test.dart';
import 'package:ladepulse_mobile/data/api.dart';
import 'package:ladepulse_mobile/data/models.dart';

void main() {
  test('pulse contract preserves denominator and pressure explanation', () {
    final pulse = PulseSnapshot.fromJson({
      'data_mode': 'synthetic_demo',
      'synthetic_notice': 'not live',
      'bucket_start': '2026-07-29T12:00:00Z',
      'source_observed_at': '2026-07-29T12:00:00Z',
      'available': 8,
      'in_use': 2,
      'out_of_service': 1,
      'stale_unknown': 1,
      'hpc_available': 4,
      'utilization': 0.2,
      'normal_utilization': 0.3,
      'coverage': {
        'inventory_connectors': 12,
        'reported_connectors': 12,
        'fresh_connectors': 11,
        'live_coverage': 11 / 12,
      },
      'pressure': {
        'utilization': 0.2,
        'offline_share': 1 / 11,
        'deviation': 0.0,
        'alternatives_gap': 0.1,
        'confidence': 0.9,
        'raw_pressure': 0.12,
        'score': 14,
        'sufficient_confidence': true,
        'weights': {
          'utilization': 0.4,
          'offline_share': 0.25,
          'deviation': 0.2,
          'alternatives_gap': 0.15,
        },
      },
      'serious_incidents': 0,
      'recovered_last_hour': 1,
    });

    expect(pulse.coverage.inventoryConnectors, 12);
    expect(pulse.coverage.freshConnectors, 11);
    expect(pulse.pressure?.weights.values.reduce((a, b) => a + b), 1);
    expect(pulse.utilization, 0.2);
  });

  test('map query sends only the selected viewport and filters', () {
    final query = MapQuery(
      west: 6,
      south: 48,
      east: 12,
      north: 53,
      zoom: 8,
      at: DateTime.utc(2026, 7, 29, 12),
      powerClass: 'hpc',
      availableNow: true,
      freshness: 'fresh',
    );

    expect(query.toQueryParameters(), {
      'west': 6.0,
      'south': 48.0,
      'east': 12.0,
      'north': 53.0,
      'zoom': 8.0,
      'at': '2026-07-29T12:00:00.000Z',
      'power_class': 'hpc',
      'available_now': true,
      'freshness': 'fresh',
    });
  });
}
