import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api.dart';
import 'models.dart';

final apiProvider = Provider<LadePulseApi>((ref) => DioLadePulseApi());

final metadataProvider = FutureProvider<Metadata>(
  (ref) => ref.watch(apiProvider).metadata(),
);

final pulseProvider = FutureProvider.autoDispose
    .family<PulseSnapshot, DateTime>(
      (ref, at) => ref.watch(apiProvider).pulse(at),
    );

final mapProvider = FutureProvider.autoDispose.family<MapResponse, MapQuery>(
  (ref, query) => ref.watch(apiProvider).map(query),
);

final stationProvider = FutureProvider.autoDispose
    .family<StationDetail, (String, DateTime)>(
      (ref, query) => ref.watch(apiProvider).station(query.$1, query.$2),
    );

final historyProvider = FutureProvider.autoDispose
    .family<StationHistory, (String, DateTime)>(
      (ref, query) => ref
          .watch(apiProvider)
          .stationHistory(
            query.$1,
            query.$2.subtract(const Duration(hours: 24)),
            query.$2,
          ),
    );
