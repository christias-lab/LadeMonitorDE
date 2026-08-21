import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timezone/data/latest.dart' as timezone;

import 'app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  timezone.initializeTimeZones();
  runApp(const ProviderScope(child: LadePulseApp()));
}
