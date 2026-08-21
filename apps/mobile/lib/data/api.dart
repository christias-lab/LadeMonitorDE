import 'package:dio/dio.dart';

import 'models.dart';

const defaultApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000',
);
const defaultDataMode = String.fromEnvironment(
  'DATA_MODE',
  defaultValue: 'synthetic_demo',
);

abstract interface class LadePulseApi {
  Future<Metadata> metadata();
  Future<PulseSnapshot> pulse(DateTime at);
  Future<MapResponse> map(MapQuery query);
  Future<StationDetail> station(String siteId, DateTime at);
  Future<StationHistory> stationHistory(
    String siteId,
    DateTime from,
    DateTime to,
  );
}

class DioLadePulseApi implements LadePulseApi {
  DioLadePulseApi({String baseUrl = defaultApiBaseUrl})
    : _dio = Dio(
        BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 8),
          receiveTimeout: const Duration(seconds: 15),
          headers: const {'accept': 'application/json'},
        ),
      );

  final Dio _dio;

  @override
  Future<Metadata> metadata() async =>
      Metadata.fromJson(await _getJson('/v1/meta'));

  @override
  Future<PulseSnapshot> pulse(DateTime at) async => PulseSnapshot.fromJson(
    await _getJson('/v1/pulse', {'at': at.toUtc().toIso8601String()}),
  );

  @override
  Future<MapResponse> map(MapQuery query) async => MapResponse.fromJson(
    await _getJson('/v1/map', query.toQueryParameters()),
  );

  @override
  Future<StationDetail> station(String siteId, DateTime at) async =>
      StationDetail.fromJson(
        await _getJson('/v1/stations/$siteId', {
          'at': at.toUtc().toIso8601String(),
        }),
      );

  @override
  Future<StationHistory> stationHistory(
    String siteId,
    DateTime from,
    DateTime to,
  ) async => StationHistory.fromJson(
    await _getJson('/v1/stations/$siteId/history', {
      'from': from.toUtc().toIso8601String(),
      'to': to.toUtc().toIso8601String(),
    }),
  );

  Future<Json> _getJson(String path, [Map<String, Object?>? query]) async {
    try {
      final parameters = <String, Object?>{
        ...?query,
        'data_mode': defaultDataMode,
      };
      final response = await _dio.get<Json>(path, queryParameters: parameters);
      final data = response.data;
      if (data == null) throw const FormatException('Empty API response');
      return data;
    } on DioException catch (error) {
      final status = error.response?.statusCode;
      throw ApiException(
        status == null
            ? 'Backend unavailable at ${_dio.options.baseUrl}'
            : 'Backend returned HTTP $status',
      );
    }
  }
}

class ApiException implements Exception {
  const ApiException(this.message);

  final String message;

  @override
  String toString() => message;
}

class MapQuery {
  const MapQuery({
    required this.west,
    required this.south,
    required this.east,
    required this.north,
    required this.zoom,
    required this.at,
    this.bundesland,
    this.powerClass,
    this.availableNow = false,
    this.freshness,
  });

  final double west;
  final double south;
  final double east;
  final double north;
  final double zoom;
  final DateTime at;
  final String? bundesland;
  final String? powerClass;
  final bool availableNow;
  final String? freshness;

  Map<String, Object?> toQueryParameters() => {
    'west': west,
    'south': south,
    'east': east,
    'north': north,
    'zoom': zoom,
    'at': at.toUtc().toIso8601String(),
    if (bundesland != null) 'bundesland': bundesland,
    if (powerClass != null) 'power_class': powerClass,
    if (availableNow) 'available_now': true,
    if (freshness != null) 'freshness': freshness,
  };

  MapQuery copyWith({
    double? west,
    double? south,
    double? east,
    double? north,
    double? zoom,
    DateTime? at,
    String? bundesland,
    bool clearBundesland = false,
    String? powerClass,
    bool clearPowerClass = false,
    bool? availableNow,
    String? freshness,
    bool clearFreshness = false,
  }) => MapQuery(
    west: west ?? this.west,
    south: south ?? this.south,
    east: east ?? this.east,
    north: north ?? this.north,
    zoom: zoom ?? this.zoom,
    at: at ?? this.at,
    bundesland: clearBundesland ? null : bundesland ?? this.bundesland,
    powerClass: clearPowerClass ? null : powerClass ?? this.powerClass,
    availableNow: availableNow ?? this.availableNow,
    freshness: clearFreshness ? null : freshness ?? this.freshness,
  );

  @override
  bool operator ==(Object other) =>
      other is MapQuery &&
      other.west == west &&
      other.south == south &&
      other.east == east &&
      other.north == north &&
      other.zoom == zoom &&
      other.at == at &&
      other.bundesland == bundesland &&
      other.powerClass == powerClass &&
      other.availableNow == availableNow &&
      other.freshness == freshness;

  @override
  int get hashCode => Object.hash(
    west,
    south,
    east,
    north,
    zoom,
    at,
    bundesland,
    powerClass,
    availableNow,
    freshness,
  );
}
