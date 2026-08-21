import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/formatters.dart';
import '../../core/strings.dart';
import '../../core/theme.dart';
import '../../data/models.dart';
import '../../data/providers.dart';
import '../../widgets/common.dart';

class StationDetailScreen extends ConsumerWidget {
  const StationDetailScreen({
    required this.siteId,
    required this.selectedAt,
    required this.onToggleLocale,
    super.key,
  });

  final String siteId;
  final DateTime selectedAt;
  final VoidCallback onToggleLocale;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(stationProvider((siteId, selectedAt)));
    return Scaffold(
      appBar: PulseAppBar(
        title: context.strings.station,
        onToggleLocale: onToggleLocale,
      ),
      body: detail.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => AsyncErrorPanel(
          error: error,
          onRetry: () => ref.invalidate(stationProvider((siteId, selectedAt))),
        ),
        data: (station) =>
            _StationBody(station: station, selectedAt: selectedAt),
      ),
    );
  }
}

class _StationBody extends ConsumerWidget {
  const _StationBody({required this.station, required this.selectedAt});

  final StationDetail station;
  final DateTime selectedAt;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final history = station.dataMode == 'synthetic_demo'
        ? ref.watch(historyProvider((station.siteId, selectedAt)))
        : null;
    final locale = Localizations.localeOf(context).languageCode;
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = math.min(1040.0, constraints.maxWidth);
        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
          child: Align(
            alignment: Alignment.topCenter,
            child: SizedBox(
              width: width,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  DataSourceBanner(
                    message: station.dataMode == 'synthetic_demo'
                        ? context.strings.synthetic
                        : station.notice,
                    dataMode: station.dataMode,
                  ),
                  const SizedBox(height: 22),
                  Text(
                    station.name,
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    [
                      station.operatorName,
                      station.address,
                      station.bundesland,
                    ].whereType<String>().join(' · '),
                    style: const TextStyle(color: PulseColors.textMuted),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    formatGermanLocal(station.requestedAt, locale),
                    style: const TextStyle(
                      color: PulseColors.accent,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 18),
                  _StateSummary(connectors: station.connectors),
                  const SizedBox(height: 18),
                  SectionTitle(context.strings.connectors),
                  const SizedBox(height: 10),
                  for (final connector in station.connectors) ...[
                    _ConnectorCard(connector: connector),
                    const SizedBox(height: 10),
                  ],
                  if (history != null) ...[
                    const SizedBox(height: 10),
                    SectionTitle(context.strings.history),
                    const SizedBox(height: 10),
                    history.when(
                      loading: () => const Card(
                        child: SizedBox(
                          height: 240,
                          child: Center(child: CircularProgressIndicator()),
                        ),
                      ),
                      error: (error, _) => Card(
                        child: Padding(
                          padding: const EdgeInsets.all(20),
                          child: Text(error.toString()),
                        ),
                      ),
                      data: (value) => _HistoryCard(history: value),
                    ),
                    const SizedBox(height: 18),
                    SectionTitle(context.strings.reliability),
                    const SizedBox(height: 10),
                    _ReliabilityCard(summary: station.reliability),
                    if (station.nearbyAlternatives.isNotEmpty) ...[
                      const SizedBox(height: 18),
                      SectionTitle(context.strings.alternatives),
                      const SizedBox(height: 10),
                      Card(
                        child: Column(
                          children: [
                            for (final alternative
                                in station.nearbyAlternatives)
                              ListTile(
                                leading: const Icon(
                                  Icons.near_me_outlined,
                                  color: PulseColors.available,
                                ),
                                title: Text(alternative.name),
                                subtitle: Text(
                                  '${alternative.distanceKm.toStringAsFixed(1)} km '
                                  '${context.strings.straightLine} · '
                                  '${alternative.maxPowerKw.toStringAsFixed(0)} kW'
                                  '${alternative.reliabilityScore == null ? '' : ' · ${alternative.reliabilityScore!.toStringAsFixed(1)}%'}',
                                ),
                                trailing: const Icon(Icons.chevron_right),
                                onTap: () => context.go(
                                  '/stations/${alternative.siteId}?at='
                                  '${Uri.encodeComponent(selectedAt.toIso8601String())}',
                                ),
                              ),
                          ],
                        ),
                      ),
                    ],
                  ],
                  const SizedBox(height: 18),
                  SectionTitle(context.strings.source),
                  const SizedBox(height: 10),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(18),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            station.sourceName,
                            style: const TextStyle(fontWeight: FontWeight.w800),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            station.publicationName,
                            style: const TextStyle(
                              color: PulseColors.textMuted,
                            ),
                          ),
                          const SizedBox(height: 12),
                          Chip(
                            avatar: const Icon(
                              Icons.verified_outlined,
                              size: 17,
                            ),
                            label: Text(station.licenceCode),
                          ),
                          if (station.attribution != null) ...[
                            const SizedBox(height: 8),
                            Text(
                              station.attribution!,
                              style: const TextStyle(
                                color: PulseColors.textMuted,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _StateSummary extends StatelessWidget {
  const _StateSummary({required this.connectors});

  final List<ConnectorStatus> connectors;

  @override
  Widget build(BuildContext context) {
    int count(String state) =>
        connectors.where((item) => item.effectiveState == state).length;
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        _StateChip(
          label: context.strings.available,
          value: count('available'),
          state: 'available',
        ),
        _StateChip(
          label: context.strings.inUse,
          value: count('in_use'),
          state: 'in_use',
        ),
        _StateChip(
          label: context.strings.offline,
          value: count('out_of_service'),
          state: 'out_of_service',
        ),
        _StateChip(
          label: context.strings.stale,
          value:
              connectors.length -
              count('available') -
              count('in_use') -
              count('out_of_service'),
          state: 'stale_unknown',
        ),
      ],
    );
  }
}

class _StateChip extends StatelessWidget {
  const _StateChip({
    required this.label,
    required this.value,
    required this.state,
  });

  final String label;
  final int value;
  final String state;

  @override
  Widget build(BuildContext context) {
    final color = statusColor(state);
    return Semantics(
      label: '$label: $value',
      child: Chip(
        avatar: Icon(Icons.circle, size: 12, color: color),
        label: Text('$value  $label'),
        side: BorderSide(color: color.withValues(alpha: 0.7)),
      ),
    );
  }
}

class _ConnectorCard extends StatelessWidget {
  const _ConnectorCard({required this.connector});

  final ConnectorStatus connector;

  @override
  Widget build(BuildContext context) {
    final color = statusColor(connector.effectiveState);
    final stateLabel = switch (connector.effectiveState) {
      'available' => context.strings.available,
      'in_use' => context.strings.inUse,
      'out_of_service' => context.strings.offline,
      _ => context.strings.stale,
    };
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 5,
              height: 66,
              decoration: BoxDecoration(
                color: color,
                borderRadius: BorderRadius.circular(4),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          '${connector.maxPowerKw.toStringAsFixed(0)} kW · '
                          '${connector.connectorType}',
                          style: const TextStyle(fontWeight: FontWeight.w800),
                        ),
                      ),
                      Text(
                        stateLabel,
                        style: TextStyle(
                          color: color,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    '${connector.evseExternalId} · ${connector.currentType}',
                    style: const TextStyle(color: PulseColors.textMuted),
                  ),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 16,
                    children: [
                      Text(
                        '${context.strings.dataAge}: '
                        '${formatAge(connector.dataAgeSeconds, context.strings.isGerman)}',
                      ),
                      if (connector.priceEurPerKwh != null)
                        Text(
                          '${connector.priceEurPerKwh!.toStringAsFixed(2)} €/kWh',
                          style: const TextStyle(
                            color: PulseColors.accent,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HistoryCard extends StatelessWidget {
  const _HistoryCard({required this.history});

  final StationHistory history;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              height: 190,
              width: double.infinity,
              child: Semantics(
                label:
                    '${context.strings.history}, '
                    '${history.points.length} ten-minute observations',
                child: CustomPaint(painter: _HistoryPainter(history.points)),
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 16,
              runSpacing: 8,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                _ChartLegend(
                  color: PulseColors.accent,
                  label: context.strings.utilization,
                ),
                _ChartLegend(
                  color: PulseColors.offline,
                  label: context.strings.offline,
                ),
                Text(
                  '${history.bucketMinutes} min',
                  style: const TextStyle(color: PulseColors.textMuted),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _HistoryPainter extends CustomPainter {
  const _HistoryPainter(this.points);

  final List<HistoryPoint> points;

  @override
  void paint(Canvas canvas, Size size) {
    if (points.length < 2) return;
    final grid = Paint()
      ..color = PulseColors.grid
      ..strokeWidth = 1;
    for (var i = 0; i <= 4; i++) {
      final y = size.height * i / 4;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }

    final utilizationPath = Path();
    for (var i = 0; i < points.length; i++) {
      final point = points[i];
      final x = size.width * i / (points.length - 1);
      final value = point.utilization ?? 0;
      final y = size.height * (1 - value.clamp(0, 1));
      if (i == 0) {
        utilizationPath.moveTo(x, y);
      } else {
        utilizationPath.lineTo(x, y);
      }
      final total =
          point.states.available +
          point.states.inUse +
          point.states.outOfService +
          point.states.staleUnknown;
      final offlineShare = total == 0 ? 0.0 : point.states.outOfService / total;
      if (offlineShare > 0) {
        canvas.drawRect(
          Rect.fromLTWH(
            x,
            size.height * (1 - offlineShare),
            math.max(1, size.width / points.length),
            size.height * offlineShare,
          ),
          Paint()..color = PulseColors.offline.withValues(alpha: 0.35),
        );
      }
    }
    canvas.drawPath(
      utilizationPath,
      Paint()
        ..color = PulseColors.accent
        ..strokeWidth = 2.5
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round,
    );
  }

  @override
  bool shouldRepaint(_HistoryPainter oldDelegate) =>
      oldDelegate.points != points;
}

class _ChartLegend extends StatelessWidget {
  const _ChartLegend({required this.color, required this.label});

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(width: 16, height: 3, color: color),
        const SizedBox(width: 5),
        Text(label, style: const TextStyle(fontSize: 12)),
      ],
    );
  }
}

class _ReliabilityCard extends StatelessWidget {
  const _ReliabilityCard({required this.summary});

  final ReliabilitySummary summary;

  @override
  Widget build(BuildContext context) {
    final metrics = [
      (context.strings.uptime, formatPercent(summary.uptime, digits: 1)),
      (
        context.strings.observable,
        formatPercent(summary.observableShare, digits: 1),
      ),
      (context.strings.outages, '${summary.outageCount}'),
      (
        context.strings.mttr,
        summary.mttrMinutes == null
            ? '—'
            : '${summary.mttrMinutes!.toStringAsFixed(0)} min',
      ),
    ];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                for (final metric in metrics)
                  SizedBox(
                    width: 190,
                    child: Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: PulseColors.surfaceHigh,
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            metric.$2,
                            style: Theme.of(context).textTheme.titleLarge
                                ?.copyWith(fontWeight: FontWeight.w900),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            metric.$1,
                            style: const TextStyle(
                              color: PulseColors.textMuted,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 14),
            Text(
              '${context.strings.dayWindow(summary.windowDays)} · '
              '${context.strings.samples(summary.sampleSize)} · '
              '${context.strings.timeWeightedEvents}',
              style: const TextStyle(color: PulseColors.textMuted),
            ),
          ],
        ),
      ),
    );
  }
}
