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

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({required this.onToggleLocale, super.key});

  final VoidCallback onToggleLocale;

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  int _stepsAgo = 0;

  @override
  Widget build(BuildContext context) {
    final metadata = ref.watch(metadataProvider);
    final reference =
        metadata.value?.referenceTime ?? DateTime.utc(2026, 7, 29, 12);
    final selectedAt = reference.subtract(Duration(minutes: _stepsAgo * 10));
    final pulse = ref.watch(pulseProvider(selectedAt));

    return Scaffold(
      appBar: PulseAppBar(
        title: context.strings.appName,
        onToggleLocale: widget.onToggleLocale,
        actions: [
          IconButton(
            tooltip: context.strings.liveMap,
            onPressed: () => _openMap(context, selectedAt),
            icon: const Icon(Icons.map_outlined),
          ),
        ],
      ),
      body: pulse.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => AsyncErrorPanel(
          error: error,
          onRetry: () => ref.invalidate(pulseProvider(selectedAt)),
        ),
        data: (snapshot) => _DashboardBody(
          snapshot: snapshot,
          selectedAt: selectedAt,
          stepsAgo: _stepsAgo,
          onTimeChanged: (value) => setState(() => _stepsAgo = value),
          onOpenMap: () => _openMap(context, selectedAt),
        ),
      ),
    );
  }

  void _openMap(BuildContext context, DateTime at) {
    context.go('/map?at=${Uri.encodeComponent(at.toUtc().toIso8601String())}');
  }
}

class _DashboardBody extends StatelessWidget {
  const _DashboardBody({
    required this.snapshot,
    required this.selectedAt,
    required this.stepsAgo,
    required this.onTimeChanged,
    required this.onOpenMap,
  });

  final PulseSnapshot snapshot;
  final DateTime selectedAt;
  final int stepsAgo;
  final ValueChanged<int> onTimeChanged;
  final VoidCallback onOpenMap;

  @override
  Widget build(BuildContext context) {
    final locale = Localizations.localeOf(context).languageCode;
    return LayoutBuilder(
      builder: (context, constraints) {
        final maxWidth = constraints.maxWidth > 1120
            ? 1120.0
            : constraints.maxWidth;
        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
          child: Align(
            alignment: Alignment.topCenter,
            child: SizedBox(
              width: maxWidth,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  DataSourceBanner(
                    message: snapshot.dataMode == 'synthetic_demo'
                        ? context.strings.synthetic
                        : snapshot.syntheticNotice,
                    dataMode: snapshot.dataMode,
                  ),
                  const SizedBox(height: 24),
                  Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              context.strings.pulse,
                              style: Theme.of(context).textTheme.headlineMedium
                                  ?.copyWith(fontWeight: FontWeight.w900),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              formatGermanLocal(snapshot.bucketStart, locale),
                              style: const TextStyle(
                                color: PulseColors.textMuted,
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (snapshot.dataMode == 'synthetic_demo')
                        _LiveDot(isNow: stepsAgo == 0)
                      else
                        const Chip(
                          avatar: Icon(Icons.inventory_2_outlined, size: 16),
                          label: Text('Official snapshot'),
                        ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  _MetricGrid(snapshot: snapshot),
                  const SizedBox(height: 18),
                  if (constraints.maxWidth >= 760)
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: _PressureCard(pressure: snapshot.pressure),
                        ),
                        const SizedBox(width: 16),
                        Expanded(child: _CoverageCard(snapshot: snapshot)),
                      ],
                    )
                  else ...[
                    _PressureCard(pressure: snapshot.pressure),
                    const SizedBox(height: 16),
                    _CoverageCard(snapshot: snapshot),
                  ],
                  const SizedBox(height: 18),
                  if (snapshot.dataMode == 'synthetic_demo') ...[
                    _TimeMachineCard(
                      selectedAt: selectedAt,
                      stepsAgo: stepsAgo,
                      onChanged: onTimeChanged,
                    ),
                    const SizedBox(height: 18),
                  ],
                  FilledButton.icon(
                    onPressed: onOpenMap,
                    icon: const Icon(Icons.public),
                    label: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      child: Text(context.strings.openMap),
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

class _MetricGrid extends StatelessWidget {
  const _MetricGrid({required this.snapshot});

  final PulseSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth >= 900
            ? 4
            : constraints.maxWidth >= 560
            ? 3
            : 2;
        final locale = Localizations.localeOf(context).languageCode;
        final cards = [
          _MetricData(
            context.strings.available,
            snapshot.available,
            PulseColors.available,
            Icons.electric_bolt,
          ),
          _MetricData(
            context.strings.inUse,
            snapshot.inUse,
            PulseColors.inUse,
            Icons.ev_station,
          ),
          _MetricData(
            context.strings.offline,
            snapshot.outOfService,
            PulseColors.offline,
            Icons.error_outline,
          ),
          _MetricData(
            context.strings.stale,
            snapshot.staleUnknown,
            PulseColors.stale,
            Icons.schedule,
          ),
          _MetricData(
            context.strings.hpcAvailable,
            snapshot.hpcAvailable,
            PulseColors.accent,
            Icons.bolt,
          ),
          _MetricData(
            context.strings.incidents,
            snapshot.seriousIncidents,
            PulseColors.offline,
            Icons.radar,
          ),
          _MetricData(
            context.strings.recovered,
            snapshot.recoveredLastHour,
            PulseColors.available,
            Icons.healing_outlined,
          ),
        ];
        return GridView.count(
          crossAxisCount: columns,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          childAspectRatio: columns == 2 ? 1.45 : 1.7,
          children: [
            for (final data in cards) _MetricCard(data: data, locale: locale),
          ],
        );
      },
    );
  }
}

class _MetricData {
  const _MetricData(this.label, this.value, this.color, this.icon);

  final String label;
  final int value;
  final Color color;
  final IconData icon;
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({required this.data, required this.locale});

  final _MetricData data;
  final String locale;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: '${data.label}: ${data.value}',
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Icon(data.icon, color: data.color, size: 22),
              Text(
                compactInteger(data.value, locale),
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                  color: data.color,
                ),
              ),
              Text(
                data.label,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: PulseColors.textMuted,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PressureCard extends StatelessWidget {
  const _PressureCard({required this.pressure});

  final Pressure? pressure;

  @override
  Widget build(BuildContext context) {
    final value = pressure;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SectionTitle(context.strings.pressure),
            const SizedBox(height: 14),
            if (value == null)
              Text(context.strings.noData)
            else ...[
              if (value.sufficientConfidence)
                Center(child: PressureGauge(score: value.score))
              else
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: PulseColors.inUse.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: PulseColors.inUse.withValues(alpha: 0.5),
                    ),
                  ),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.visibility_off_outlined,
                        color: PulseColors.inUse,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(context.strings.insufficientConfidence),
                      ),
                    ],
                  ),
                ),
              const SizedBox(height: 16),
              Text(
                context.strings.methodology,
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 10),
              _ComponentBar(
                label: context.strings.utilization,
                value: value.utilization,
              ),
              _ComponentBar(
                label: context.strings.offline,
                value: value.offlineShare,
              ),
              _ComponentBar(
                label: context.strings.normal,
                value: value.deviation,
              ),
              _ComponentBar(
                label: context.strings.alternativesGap,
                value: value.alternativesGap,
              ),
              const Divider(height: 24),
              _ComponentBar(
                label: context.strings.confidence,
                value: value.confidence,
                color: PulseColors.available,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class PressureGauge extends StatelessWidget {
  const PressureGauge({required this.score, super.key});

  final int score;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: '${context.strings.pressure}: $score of 100',
      child: SizedBox(
        width: 180,
        height: 106,
        child: CustomPaint(
          painter: _GaugePainter(score / 100),
          child: Align(
            alignment: Alignment.bottomCenter,
            child: Text(
              '$score',
              style: Theme.of(
                context,
              ).textTheme.displaySmall?.copyWith(fontWeight: FontWeight.w900),
            ),
          ),
        ),
      ),
    );
  }
}

class _GaugePainter extends CustomPainter {
  const _GaugePainter(this.value);

  final double value;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Rect.fromLTWH(10, 8, size.width - 20, (size.width - 20) * 0.9);
    const start = math.pi;
    const sweep = math.pi;
    final background = Paint()
      ..color = PulseColors.grid
      ..strokeWidth = 14
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    final foreground = Paint()
      ..shader = const LinearGradient(
        colors: [PulseColors.available, PulseColors.inUse, PulseColors.offline],
      ).createShader(rect)
      ..strokeWidth = 14
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(rect, start, sweep, false, background);
    canvas.drawArc(rect, start, sweep * value.clamp(0, 1), false, foreground);
  }

  @override
  bool shouldRepaint(_GaugePainter oldDelegate) => oldDelegate.value != value;
}

class _ComponentBar extends StatelessWidget {
  const _ComponentBar({
    required this.label,
    required this.value,
    this.color = PulseColors.accent,
  });

  final String label;
  final double value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: [
          Expanded(child: Text(label, style: const TextStyle(fontSize: 13))),
          SizedBox(
            width: 100,
            child: LinearProgressIndicator(
              value: value.clamp(0, 1),
              color: color,
              minHeight: 7,
              borderRadius: BorderRadius.circular(8),
            ),
          ),
          const SizedBox(width: 9),
          SizedBox(width: 36, child: Text(formatPercent(value))),
        ],
      ),
    );
  }
}

class _CoverageCard extends StatelessWidget {
  const _CoverageCard({required this.snapshot});

  final PulseSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final coverage = snapshot.coverage;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SectionTitle(context.strings.liveCoverage),
            const SizedBox(height: 18),
            Text(
              formatPercent(coverage.liveCoverage, digits: 1),
              style: Theme.of(context).textTheme.displaySmall?.copyWith(
                fontWeight: FontWeight.w900,
                color: PulseColors.available,
              ),
            ),
            const SizedBox(height: 10),
            LinearProgressIndicator(
              value: coverage.liveCoverage,
              minHeight: 10,
              borderRadius: BorderRadius.circular(10),
            ),
            const SizedBox(height: 18),
            _KeyValue(
              label: context.strings.inventoryDenominator,
              value: '${coverage.inventoryConnectors}',
            ),
            _KeyValue(
              label: context.strings.reported,
              value: '${coverage.reportedConnectors}',
            ),
            _KeyValue(
              label: context.strings.fresh,
              value: '${coverage.freshConnectors}',
            ),
            const Divider(height: 28),
            _KeyValue(
              label: context.strings.utilization,
              value: formatPercent(snapshot.utilization, digits: 1),
            ),
            _KeyValue(
              label: context.strings.normal,
              value: formatPercent(snapshot.normalUtilization, digits: 1),
            ),
          ],
        ),
      ),
    );
  }
}

class _KeyValue extends StatelessWidget {
  const _KeyValue({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: const TextStyle(color: PulseColors.textMuted),
            ),
          ),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}

class _TimeMachineCard extends StatelessWidget {
  const _TimeMachineCard({
    required this.selectedAt,
    required this.stepsAgo,
    required this.onChanged,
  });

  final DateTime selectedAt;
  final int stepsAgo;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    final locale = Localizations.localeOf(context).languageCode;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SectionTitle(
              context.strings.timeMachine,
              trailing: Text(
                stepsAgo == 0 ? context.strings.now : '-${stepsAgo * 10} min',
                style: const TextStyle(color: PulseColors.accent),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '${context.strings.selectedTime}: '
              '${formatGermanLocal(selectedAt, locale)}',
              style: const TextStyle(color: PulseColors.textMuted),
            ),
            Slider(
              value: stepsAgo.toDouble(),
              min: 0,
              max: 144,
              divisions: 144,
              label: stepsAgo == 0
                  ? context.strings.now
                  : '-${stepsAgo * 10} min',
              onChanged: (value) => onChanged(value.round()),
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [Text(context.strings.now), const Text('−24 h')],
            ),
          ],
        ),
      ),
    );
  }
}

class _LiveDot extends StatelessWidget {
  const _LiveDot({required this.isNow});

  final bool isNow;

  @override
  Widget build(BuildContext context) {
    return Chip(
      avatar: Icon(
        isNow ? Icons.circle : Icons.history,
        size: 12,
        color: isNow ? PulseColors.available : PulseColors.accent,
      ),
      label: Text(isNow ? context.strings.now : context.strings.timeMachine),
    );
  }
}
