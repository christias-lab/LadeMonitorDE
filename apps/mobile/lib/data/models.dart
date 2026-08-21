typedef Json = Map<String, dynamic>;

double _double(Object? value) => (value as num).toDouble();
double? _nullableDouble(Object? value) =>
    value == null ? null : (value as num).toDouble();
DateTime _date(Object? value) => DateTime.parse(value! as String).toUtc();
DateTime? _nullableDate(Object? value) =>
    value == null ? null : DateTime.parse(value as String).toUtc();

class Metadata {
  const Metadata({
    required this.product,
    required this.tagline,
    required this.dataMode,
    required this.syntheticNotice,
    required this.referenceTime,
    required this.mapStyleUrl,
  });

  factory Metadata.fromJson(Json json) => Metadata(
    product: json['product'] as String,
    tagline: json['tagline'] as String,
    dataMode: json['data_mode'] as String,
    syntheticNotice: json['synthetic_notice'] as String,
    referenceTime: _date(json['reference_time']),
    mapStyleUrl: json['map_style_url'] as String,
  );

  final String product;
  final String tagline;
  final String dataMode;
  final String syntheticNotice;
  final DateTime referenceTime;
  final String mapStyleUrl;
}

class Coverage {
  const Coverage({
    required this.inventoryConnectors,
    required this.reportedConnectors,
    required this.freshConnectors,
    required this.liveCoverage,
  });

  factory Coverage.fromJson(Json json) => Coverage(
    inventoryConnectors: json['inventory_connectors'] as int,
    reportedConnectors: json['reported_connectors'] as int,
    freshConnectors: json['fresh_connectors'] as int,
    liveCoverage: _double(json['live_coverage']),
  );

  final int inventoryConnectors;
  final int reportedConnectors;
  final int freshConnectors;
  final double liveCoverage;
}

class Pressure {
  const Pressure({
    required this.utilization,
    required this.offlineShare,
    required this.deviation,
    required this.alternativesGap,
    required this.confidence,
    required this.rawPressure,
    required this.score,
    required this.sufficientConfidence,
    required this.weights,
  });

  factory Pressure.fromJson(Json json) => Pressure(
    utilization: _double(json['utilization']),
    offlineShare: _double(json['offline_share']),
    deviation: _double(json['deviation']),
    alternativesGap: _double(json['alternatives_gap']),
    confidence: _double(json['confidence']),
    rawPressure: _double(json['raw_pressure']),
    score: json['score'] as int,
    sufficientConfidence: json['sufficient_confidence'] as bool,
    weights: (json['weights'] as Json).map(
      (key, value) => MapEntry(key, _double(value)),
    ),
  );

  final double utilization;
  final double offlineShare;
  final double deviation;
  final double alternativesGap;
  final double confidence;
  final double rawPressure;
  final int score;
  final bool sufficientConfidence;
  final Map<String, double> weights;
}

class PulseSnapshot {
  const PulseSnapshot({
    required this.dataMode,
    required this.syntheticNotice,
    required this.bucketStart,
    required this.sourceObservedAt,
    required this.available,
    required this.inUse,
    required this.outOfService,
    required this.staleUnknown,
    required this.hpcAvailable,
    required this.utilization,
    required this.normalUtilization,
    required this.coverage,
    required this.pressure,
    required this.seriousIncidents,
    required this.recoveredLastHour,
  });

  factory PulseSnapshot.fromJson(Json json) => PulseSnapshot(
    dataMode: json['data_mode'] as String,
    syntheticNotice: json['synthetic_notice'] as String,
    bucketStart: _date(json['bucket_start']),
    sourceObservedAt: _date(json['source_observed_at']),
    available: json['available'] as int,
    inUse: json['in_use'] as int,
    outOfService: json['out_of_service'] as int,
    staleUnknown: json['stale_unknown'] as int,
    hpcAvailable: json['hpc_available'] as int,
    utilization: _nullableDouble(json['utilization']),
    normalUtilization: _nullableDouble(json['normal_utilization']),
    coverage: Coverage.fromJson(json['coverage'] as Json),
    pressure: json['pressure'] == null
        ? null
        : Pressure.fromJson(json['pressure'] as Json),
    seriousIncidents: json['serious_incidents'] as int,
    recoveredLastHour: json['recovered_last_hour'] as int,
  );

  final String dataMode;
  final String syntheticNotice;
  final DateTime bucketStart;
  final DateTime sourceObservedAt;
  final int available;
  final int inUse;
  final int outOfService;
  final int staleUnknown;
  final int hpcAvailable;
  final double? utilization;
  final double? normalUtilization;
  final Coverage coverage;
  final Pressure? pressure;
  final int seriousIncidents;
  final int recoveredLastHour;
}

class StateCounts {
  const StateCounts({
    required this.available,
    required this.inUse,
    required this.outOfService,
    required this.staleUnknown,
  });

  factory StateCounts.fromJson(Json json) => StateCounts(
    available: json['available'] as int,
    inUse: json['in_use'] as int,
    outOfService: json['out_of_service'] as int,
    staleUnknown: json['stale_unknown'] as int,
  );

  final int available;
  final int inUse;
  final int outOfService;
  final int staleUnknown;
}

class MapFeature {
  const MapFeature({
    required this.kind,
    required this.id,
    required this.siteId,
    required this.name,
    required this.bundesland,
    required this.latitude,
    required this.longitude,
    required this.siteCount,
    required this.connectorCount,
    required this.states,
    required this.utilization,
    required this.offlineShare,
    required this.confidence,
    required this.maxPowerKw,
    required this.newSeriousOutage,
  });

  factory MapFeature.fromJson(Json json) => MapFeature(
    kind: json['kind'] as String,
    id: json['id'] as String,
    siteId: json['site_id'] as String?,
    name: json['name'] as String,
    bundesland: json['bundesland'] as String?,
    latitude: _double(json['latitude']),
    longitude: _double(json['longitude']),
    siteCount: json['site_count'] as int,
    connectorCount: json['connector_count'] as int,
    states: StateCounts.fromJson(json['states'] as Json),
    utilization: _nullableDouble(json['utilization']),
    offlineShare: _nullableDouble(json['offline_share']),
    confidence: _double(json['confidence']),
    maxPowerKw: _double(json['max_power_kw']),
    newSeriousOutage: json['new_serious_outage'] as bool,
  );

  final String kind;
  final String id;
  final String? siteId;
  final String name;
  final String? bundesland;
  final double latitude;
  final double longitude;
  final int siteCount;
  final int connectorCount;
  final StateCounts states;
  final double? utilization;
  final double? offlineShare;
  final double confidence;
  final double maxPowerKw;
  final bool newSeriousOutage;
}

class MapResponse {
  const MapResponse({
    required this.dataMode,
    required this.notice,
    required this.requestedAt,
    required this.clustered,
    required this.truncated,
    required this.features,
  });

  factory MapResponse.fromJson(Json json) => MapResponse(
    dataMode: json['data_mode'] as String,
    notice: json['synthetic_notice'] as String,
    requestedAt: _date(json['requested_at']),
    clustered: json['clustered'] as bool,
    truncated: json['truncated'] as bool,
    features: (json['features'] as List<Object?>)
        .map((item) => MapFeature.fromJson(item! as Json))
        .toList(growable: false),
  );

  final String dataMode;
  final String notice;
  final DateTime requestedAt;
  final bool clustered;
  final bool truncated;
  final List<MapFeature> features;
}

class ConnectorStatus {
  const ConnectorStatus({
    required this.externalId,
    required this.evseExternalId,
    required this.connectorType,
    required this.maxPowerKw,
    required this.currentType,
    required this.physicalState,
    required this.effectiveState,
    required this.sourceObservedAt,
    required this.dataAgeSeconds,
    required this.priceEurPerKwh,
  });

  factory ConnectorStatus.fromJson(Json json) => ConnectorStatus(
    externalId: json['external_id'] as String,
    evseExternalId: json['evse_external_id'] as String,
    connectorType: json['connector_type'] as String,
    maxPowerKw: _double(json['max_power_kw']),
    currentType: json['current_type'] as String,
    physicalState: json['physical_state'] as String,
    effectiveState: json['effective_state'] as String,
    sourceObservedAt: _nullableDate(json['source_observed_at']),
    dataAgeSeconds: json['data_age_seconds'] as int?,
    priceEurPerKwh: _nullableDouble(json['price_eur_per_kwh']),
  );

  final String externalId;
  final String evseExternalId;
  final String connectorType;
  final double maxPowerKw;
  final String currentType;
  final String physicalState;
  final String effectiveState;
  final DateTime? sourceObservedAt;
  final int? dataAgeSeconds;
  final double? priceEurPerKwh;
}

class ReliabilitySummary {
  const ReliabilitySummary({
    required this.windowDays,
    required this.uptime,
    required this.observableShare,
    required this.outageCount,
    required this.medianOutageMinutes,
    required this.mttrMinutes,
    required this.sampleSize,
  });

  factory ReliabilitySummary.fromJson(Json json) => ReliabilitySummary(
    windowDays: json['window_days'] as int,
    uptime: _nullableDouble(json['uptime']),
    observableShare: _double(json['observable_share']),
    outageCount: json['outage_count'] as int,
    medianOutageMinutes: _nullableDouble(json['median_outage_minutes']),
    mttrMinutes: _nullableDouble(json['mttr_minutes']),
    sampleSize: json['sample_size'] as int,
  );

  final int windowDays;
  final double? uptime;
  final double observableShare;
  final int outageCount;
  final double? medianOutageMinutes;
  final double? mttrMinutes;
  final int sampleSize;
}

class AlternativeSite {
  const AlternativeSite({
    required this.siteId,
    required this.name,
    required this.distanceKm,
    required this.maxPowerKw,
    required this.reliabilityScore,
  });

  factory AlternativeSite.fromJson(Json json) => AlternativeSite(
    siteId: json['site_id'] as String,
    name: json['name'] as String,
    distanceKm: _double(json['distance_km_straight_line']),
    maxPowerKw: _double(json['max_power_kw']),
    reliabilityScore: _nullableDouble(json['reliability_score']),
  );

  final String siteId;
  final String name;
  final double distanceKm;
  final double maxPowerKw;
  final double? reliabilityScore;
}

class StationDetail {
  const StationDetail({
    required this.dataMode,
    required this.notice,
    required this.siteId,
    required this.name,
    required this.address,
    required this.bundesland,
    required this.operatorName,
    required this.requestedAt,
    required this.connectors,
    required this.reliability,
    required this.nearbyAlternatives,
    required this.sourceName,
    required this.publicationName,
    required this.licenceCode,
    required this.attribution,
  });

  factory StationDetail.fromJson(Json json) => StationDetail(
    dataMode: json['data_mode'] as String,
    notice: json['synthetic_notice'] as String,
    siteId: json['site_id'] as String,
    name: json['name'] as String,
    address: json['address'] as String?,
    bundesland: json['bundesland'] as String,
    operatorName: json['operator_name'] as String,
    requestedAt: _date(json['requested_at']),
    connectors: (json['connectors'] as List<Object?>)
        .map((item) => ConnectorStatus.fromJson(item! as Json))
        .toList(growable: false),
    reliability: ReliabilitySummary.fromJson(json['reliability'] as Json),
    nearbyAlternatives: (json['nearby_alternatives'] as List<Object?>)
        .map((item) => AlternativeSite.fromJson(item! as Json))
        .toList(growable: false),
    sourceName: json['source_name'] as String,
    publicationName: json['publication_name'] as String,
    licenceCode: json['licence_code'] as String,
    attribution: json['attribution'] as String?,
  );

  final String dataMode;
  final String notice;
  final String siteId;
  final String name;
  final String? address;
  final String bundesland;
  final String operatorName;
  final DateTime requestedAt;
  final List<ConnectorStatus> connectors;
  final ReliabilitySummary reliability;
  final List<AlternativeSite> nearbyAlternatives;
  final String sourceName;
  final String publicationName;
  final String licenceCode;
  final String? attribution;
}

class HistoryPoint {
  const HistoryPoint({
    required this.bucketStart,
    required this.states,
    required this.utilization,
    required this.observableConnectors,
  });

  factory HistoryPoint.fromJson(Json json) => HistoryPoint(
    bucketStart: _date(json['bucket_start']),
    states: StateCounts.fromJson(json['states'] as Json),
    utilization: _nullableDouble(json['utilization']),
    observableConnectors: json['observable_connectors'] as int,
  );

  final DateTime bucketStart;
  final StateCounts states;
  final double? utilization;
  final int observableConnectors;
}

class StationHistory {
  const StationHistory({required this.bucketMinutes, required this.points});

  factory StationHistory.fromJson(Json json) => StationHistory(
    bucketMinutes: json['bucket_minutes'] as int,
    points: (json['points'] as List<Object?>)
        .map((item) => HistoryPoint.fromJson(item! as Json))
        .toList(growable: false),
  );

  final int bucketMinutes;
  final List<HistoryPoint> points;
}
