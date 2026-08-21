import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:maplibre_gl/maplibre_gl.dart';

import '../../core/strings.dart';
import '../../core/theme.dart';
import '../../data/api.dart';
import '../../data/models.dart';
import '../../data/providers.dart';
import '../../widgets/common.dart';

class LiveMapScreen extends ConsumerStatefulWidget {
  const LiveMapScreen({
    required this.selectedAt,
    required this.onToggleLocale,
    super.key,
  });

  final DateTime selectedAt;
  final VoidCallback onToggleLocale;

  @override
  ConsumerState<LiveMapScreen> createState() => _LiveMapScreenState();
}

class _LiveMapScreenState extends ConsumerState<LiveMapScreen> {
  late MapQuery _query;
  MapLibreMapController? _controller;
  MapResponse? _latestResponse;
  bool _styleReady = false;
  bool _pulseOn = false;
  Timer? _pulseTimer;

  @override
  void initState() {
    super.initState();
    _query = MapQuery(
      west: 5.5,
      south: 47.0,
      east: 15.5,
      north: 55.3,
      zoom: 5.4,
      at: widget.selectedAt,
    );
  }

  @override
  void dispose() {
    _pulseTimer?.cancel();
    _controller?.onCircleTapped.remove(_onCircleTapped);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final response = ref.watch(mapProvider(_query));
    final metadata = ref.watch(metadataProvider);
    ref.listen(mapProvider(_query), (_, next) {
      next.whenData((data) {
        _latestResponse = data;
        _configurePulse(data);
        unawaited(_renderFeatures(data));
      });
    });
    final styleUrl =
        metadata.value?.mapStyleUrl ??
        'https://demotiles.maplibre.org/style.json';

    return Scaffold(
      appBar: PulseAppBar(
        title: context.strings.liveMap,
        onToggleLocale: widget.onToggleLocale,
      ),
      body: Stack(
        children: [
          MapLibreMap(
            styleString: styleUrl,
            initialCameraPosition: const CameraPosition(
              target: LatLng(51.16, 10.45),
              zoom: 5.4,
            ),
            minMaxZoomPreference: const MinMaxZoomPreference(4, 17),
            rotateGesturesEnabled: false,
            compassEnabled: false,
            attributionButtonPosition: AttributionButtonPosition.bottomRight,
            onMapCreated: _onMapCreated,
            onStyleLoadedCallback: _onStyleLoaded,
            onCameraIdle: _onCameraIdle,
          ),
          Positioned(
            top: 12,
            left: 12,
            right: 12,
            child: DataSourceBanner(
              message:
                  (response.value?.dataMode ??
                          metadata.value?.dataMode ??
                          'synthetic_demo') ==
                      'synthetic_demo'
                  ? context.strings.synthetic
                  : response.value?.notice ??
                        metadata.value?.syntheticNotice ??
                        context.strings.synthetic,
              dataMode:
                  response.value?.dataMode ??
                  metadata.value?.dataMode ??
                  'synthetic_demo',
              compact: true,
            ),
          ),
          Positioned(
            top: 72,
            left: 8,
            right: 8,
            child: _FilterBar(
              query: _query,
              onPowerChanged: _setPowerClass,
              onBundeslandChanged: _setBundesland,
              onAvailableChanged: (value) {
                setState(() => _query = _query.copyWith(availableNow: value));
              },
              onFreshChanged: (value) {
                setState(
                  () => _query = _query.copyWith(
                    freshness: value ? 'fresh' : null,
                    clearFreshness: !value,
                  ),
                );
              },
            ),
          ),
          Positioned(
            left: 12,
            right: 12,
            bottom: 12,
            child: _MapLegend(response: response),
          ),
          if (response.isLoading)
            const Positioned(
              top: 132,
              right: 16,
              child: Card(
                child: Padding(
                  padding: EdgeInsets.all(10),
                  child: SizedBox.square(
                    dimension: 22,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),
              ),
            ),
          if (response.hasError)
            Positioned(
              top: 132,
              left: 16,
              right: 16,
              child: Material(
                color: PulseColors.surface,
                borderRadius: BorderRadius.circular(12),
                child: ListTile(
                  leading: const Icon(
                    Icons.cloud_off,
                    color: PulseColors.offline,
                  ),
                  title: Text(response.error.toString()),
                  trailing: IconButton(
                    onPressed: () => ref.invalidate(mapProvider(_query)),
                    icon: const Icon(Icons.refresh),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  void _onMapCreated(MapLibreMapController controller) {
    _controller = controller;
    controller.onCircleTapped.add(_onCircleTapped);
  }

  void _onStyleLoaded() {
    _styleReady = true;
    final response = _latestResponse;
    if (response != null) unawaited(_renderFeatures(response));
  }

  Future<void> _onCameraIdle() async {
    final controller = _controller;
    if (controller == null) return;
    final bounds = await controller.getVisibleRegion();
    final zoom = controller.cameraPosition?.zoom ?? _query.zoom;
    if (!mounted) return;
    setState(() {
      _query = _query.copyWith(
        west: _rounded(bounds.southwest.longitude),
        south: _rounded(bounds.southwest.latitude),
        east: _rounded(bounds.northeast.longitude),
        north: _rounded(bounds.northeast.latitude),
        zoom: _rounded(zoom),
      );
    });
  }

  void _setPowerClass(String? value) {
    setState(
      () => _query = _query.copyWith(
        powerClass: value,
        clearPowerClass: value == null,
      ),
    );
  }

  void _setBundesland(String? value) {
    setState(
      () => _query = _query.copyWith(
        bundesland: value,
        clearBundesland: value == null,
      ),
    );
  }

  Future<void> _renderFeatures(MapResponse response) async {
    final controller = _controller;
    if (controller == null || !_styleReady) return;
    await controller.clearCircles();
    if (!mounted || response.features.isEmpty) return;
    final options = <CircleOptions>[];
    final data = <Map<String, dynamic>>[];
    for (final feature in response.features) {
      final outagePulse = feature.newSeriousOutage && _pulseOn;
      options.add(
        CircleOptions(
          geometry: LatLng(feature.latitude, feature.longitude),
          circleRadius:
              6 +
              math.min(20, math.sqrt(feature.connectorCount) * 1.6) +
              (outagePulse ? 5 : 0),
          circleColor: _utilizationColor(feature.utilization),
          circleOpacity: (0.30 + 0.70 * feature.confidence).clamp(0.30, 1),
          circleStrokeColor: feature.newSeriousOutage
              ? '#F05D8A'
              : _offlineRingColor(feature.offlineShare),
          circleStrokeWidth:
              1.5 + 6 * (feature.offlineShare ?? 0) + (outagePulse ? 3 : 0),
          circleBlur: outagePulse ? 0.35 : 0,
        ),
      );
      data.add({
        'kind': feature.kind,
        'siteId': feature.siteId,
        'latitude': feature.latitude,
        'longitude': feature.longitude,
      });
    }
    await controller.addCircles(options, data);
  }

  void _onCircleTapped(Circle circle) {
    final data = circle.data;
    if (data == null) return;
    if (data['kind'] == 'cluster') {
      final currentZoom = _controller?.cameraPosition?.zoom ?? _query.zoom;
      unawaited(
        _controller?.animateCamera(
          CameraUpdate.newLatLngZoom(
            LatLng(
              (data['latitude'] as num).toDouble(),
              (data['longitude'] as num).toDouble(),
            ),
            math.min(17, currentZoom + 2),
          ),
        ),
      );
      return;
    }
    final siteId = data['siteId'] as String?;
    if (siteId != null && mounted) {
      context.go(
        '/stations/$siteId?at='
        '${Uri.encodeComponent(widget.selectedAt.toUtc().toIso8601String())}',
      );
    }
  }

  void _configurePulse(MapResponse response) {
    final hasOutage = response.features.any((item) => item.newSeriousOutage);
    if (!hasOutage) {
      _pulseTimer?.cancel();
      _pulseTimer = null;
      return;
    }
    _pulseTimer ??= Timer.periodic(const Duration(milliseconds: 850), (_) {
      _pulseOn = !_pulseOn;
      final latest = _latestResponse;
      if (latest != null) unawaited(_renderFeatures(latest));
    });
  }

  static double _rounded(double value) =>
      (value * 10000).roundToDouble() / 10000;

  static String _utilizationColor(double? value) {
    if (value == null) return '#91A0AE';
    if (value < 0.4) return '#36D6C0';
    if (value < 0.75) return '#F6C85F';
    return '#F05D8A';
  }

  static String _offlineRingColor(double? value) =>
      (value ?? 0) >= 0.15 ? '#F05D8A' : '#07111D';
}

class _FilterBar extends StatelessWidget {
  const _FilterBar({
    required this.query,
    required this.onPowerChanged,
    required this.onBundeslandChanged,
    required this.onAvailableChanged,
    required this.onFreshChanged,
  });

  final MapQuery query;
  final ValueChanged<String?> onPowerChanged;
  final ValueChanged<String?> onBundeslandChanged;
  final ValueChanged<bool> onAvailableChanged;
  final ValueChanged<bool> onFreshChanged;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: PulseColors.background.withValues(alpha: 0.94),
      child: SizedBox(
        height: 52,
        child: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          scrollDirection: Axis.horizontal,
          children: [
            PopupMenuButton<String?>(
              initialValue: query.bundesland,
              onSelected: onBundeslandChanged,
              itemBuilder: (context) => [
                PopupMenuItem(
                  value: null,
                  child: Text(
                    context.strings.isGerman
                        ? 'Alle Bundesländer'
                        : 'All federal states',
                  ),
                ),
                for (final state in _bundeslaender)
                  PopupMenuItem(value: state, child: Text(state)),
              ],
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 10),
                child: Row(
                  children: [
                    const Icon(Icons.location_on_outlined, size: 18),
                    const SizedBox(width: 5),
                    Text(
                      query.bundesland ??
                          (context.strings.isGerman
                              ? 'Bundesland'
                              : 'Federal state'),
                    ),
                    const Icon(Icons.arrow_drop_down),
                  ],
                ),
              ),
            ),
            const VerticalDivider(indent: 10, endIndent: 10),
            PopupMenuButton<String?>(
              initialValue: query.powerClass,
              onSelected: onPowerChanged,
              itemBuilder: (context) => [
                PopupMenuItem(
                  value: null,
                  child: Text(context.strings.allPower),
                ),
                const PopupMenuItem(value: 'ac', child: Text('AC ≤ 22 kW')),
                const PopupMenuItem(value: 'dc', child: Text('DC 23–149 kW')),
                const PopupMenuItem(value: 'hpc', child: Text('HPC ≥ 150 kW')),
              ],
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 10),
                child: Row(
                  children: [
                    const Icon(Icons.bolt, size: 18),
                    const SizedBox(width: 5),
                    Text(
                      query.powerClass?.toUpperCase() ??
                          context.strings.allPower,
                    ),
                    const Icon(Icons.arrow_drop_down),
                  ],
                ),
              ),
            ),
            const VerticalDivider(indent: 10, endIndent: 10),
            FilterChip(
              selected: query.availableNow,
              onSelected: onAvailableChanged,
              avatar: const Icon(Icons.check_circle_outline, size: 17),
              label: Text(context.strings.availableNow),
            ),
            const SizedBox(width: 8),
            FilterChip(
              selected: query.freshness == 'fresh',
              onSelected: onFreshChanged,
              avatar: const Icon(Icons.schedule, size: 17),
              label: Text(context.strings.freshOnly),
            ),
          ],
        ),
      ),
    );
  }
}

const _bundeslaender = [
  'Baden-Württemberg',
  'Bayern',
  'Berlin',
  'Brandenburg',
  'Bremen',
  'Hamburg',
  'Hessen',
  'Mecklenburg-Vorpommern',
  'Niedersachsen',
  'Nordrhein-Westfalen',
  'Rheinland-Pfalz',
  'Saarland',
  'Sachsen',
  'Sachsen-Anhalt',
  'Schleswig-Holstein',
  'Thüringen',
];

class _MapLegend extends StatelessWidget {
  const _MapLegend({required this.response});

  final AsyncValue<MapResponse> response;

  @override
  Widget build(BuildContext context) {
    final count = response.value?.features.length;
    final clustered = response.value?.clustered ?? false;
    return Card(
      color: PulseColors.background.withValues(alpha: 0.94),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const _LegendDot(color: PulseColors.available),
                const _LegendDot(color: PulseColors.inUse),
                const _LegendDot(color: PulseColors.offline),
                const Spacer(),
                if (count != null)
                  Text(
                    '$count '
                    '${clustered ? context.strings.clusters : context.strings.sites}',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
              ],
            ),
            const SizedBox(height: 5),
            Text(
              context.strings.mapLegend,
              style: const TextStyle(
                color: PulseColors.textMuted,
                fontSize: 11,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LegendDot extends StatelessWidget {
  const _LegendDot({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 15,
      height: 15,
      margin: const EdgeInsets.only(right: 7),
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color,
        border: Border.all(color: Colors.white54, width: 2),
      ),
    );
  }
}
