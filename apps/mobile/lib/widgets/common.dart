import 'package:flutter/material.dart';

import '../core/strings.dart';
import '../core/theme.dart';

class PulseAppBar extends StatelessWidget implements PreferredSizeWidget {
  const PulseAppBar({
    required this.title,
    required this.onToggleLocale,
    this.actions = const [],
    super.key,
  });

  final String title;
  final VoidCallback onToggleLocale;
  final List<Widget> actions;

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) {
    return AppBar(
      titleSpacing: 20,
      title: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.bolt_rounded, color: PulseColors.available),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              title,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
          ),
        ],
      ),
      actions: [
        ...actions,
        Semantics(
          button: true,
          label: 'Deutsch / English',
          child: TextButton(
            onPressed: onToggleLocale,
            child: Text(context.strings.isGerman ? 'EN' : 'DE'),
          ),
        ),
        const SizedBox(width: 8),
      ],
    );
  }
}

class DataSourceBanner extends StatelessWidget {
  const DataSourceBanner({
    required this.message,
    required this.dataMode,
    super.key,
    this.compact = false,
  });

  final String message;
  final String dataMode;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      label: message,
      child: Container(
        width: double.infinity,
        padding: EdgeInsets.symmetric(
          horizontal: compact ? 12 : 16,
          vertical: compact ? 8 : 11,
        ),
        decoration: BoxDecoration(
          color: PulseColors.inUse.withValues(alpha: 0.12),
          border: Border.all(color: PulseColors.inUse.withValues(alpha: 0.55)),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Icon(
              dataMode == 'synthetic_demo'
                  ? Icons.science_outlined
                  : Icons.verified_outlined,
              color: PulseColors.inUse,
              size: 20,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                message,
                style: const TextStyle(
                  color: PulseColors.inUse,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class AsyncErrorPanel extends StatelessWidget {
  const AsyncErrorPanel({
    required this.error,
    required this.onRetry,
    super.key,
  });

  final Object error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.cloud_off_outlined,
                    size: 44,
                    color: PulseColors.offline,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    error.toString(),
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: PulseColors.textMuted),
                  ),
                  const SizedBox(height: 16),
                  FilledButton.icon(
                    onPressed: onRetry,
                    icon: const Icon(Icons.refresh),
                    label: Text(context.strings.retry),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class SectionTitle extends StatelessWidget {
  const SectionTitle(this.title, {this.trailing, super.key});

  final String title;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(
            title,
            style: Theme.of(
              context,
            ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
          ),
        ),
        ?trailing,
      ],
    );
  }
}
