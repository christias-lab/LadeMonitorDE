import 'package:intl/intl.dart';
import 'package:timezone/timezone.dart' as timezone;

final _berlin = timezone.getLocation('Europe/Berlin');

String formatGermanLocal(DateTime utc, String languageCode) {
  final local = timezone.TZDateTime.from(utc.toUtc(), _berlin);
  return DateFormat(
    languageCode == 'de' ? 'EEE, dd.MM. · HH:mm' : 'EEE, MMM d · HH:mm',
    languageCode,
  ).format(local);
}

String formatPercent(num? value, {int digits = 0}) {
  if (value == null) return '—';
  return '${(value * 100).toStringAsFixed(digits)}%';
}

String compactInteger(int value, String locale) =>
    NumberFormat.compact(locale: locale).format(value);

String formatAge(int? seconds, bool german) {
  if (seconds == null) return '—';
  if (seconds < 60) return '${seconds}s';
  if (seconds < 3600) return '${seconds ~/ 60} min';
  return german ? '${seconds ~/ 3600} Std.' : '${seconds ~/ 3600} h';
}
