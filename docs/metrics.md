# Metric definitions

## Connector state

Normalized physical states:

- `available`
- `in_use`
- `out_of_service`
- `unknown`

Freshness is orthogonal. Once an observation exceeds its source threshold, its effective aggregate state is `stale_unknown`; it is not counted as offline.

## Utilization

```text
utilization = in_use / (available + in_use)
```

If the denominator is zero, utilization is `null`, never zero. Offline and unknown connectors are excluded.

## Coverage

Every aggregate returns:

- `reported_connectors`: connectors with an observation in the requested bucket;
- `fresh_connectors`: connectors whose observation remains within the source threshold;
- `inventory_connectors`: connectors in the selected inventory scope;
- `live_coverage = fresh_connectors / inventory_connectors`;
- source/publication breakdown where relevant.

## Charging Pressure Index

All components are normalized to `[0, 1]`.

```text
U = known-state utilization
O = out_of_service / (available + in_use + out_of_service)
D = clamp((U - normal_utilization) / max(0.10, 1 - normal_utilization), 0, 1)
R = lack of reliable alternatives
C = live_coverage × freshness_quality × identifier_completeness

raw_pressure = 0.40·U + 0.25·O + 0.20·D + 0.15·R
pressure = round(100 × (C·raw_pressure + (1−C)·0.50))
```

The API returns `U`, `O`, `D`, `R`, `C`, weights, raw pressure, final score, and denominator. When `C < 0.50`, the UI suppresses the score headline and shows insufficient confidence.

Phase 1's alternative calculation uses Haversine straight-line distance and labels it accordingly. Driving distance is not implied.

## Uptime and recovery

Uptime is the duration in an operational state divided by observable duration. It is integrated over status-event intervals, not counted records.

- `observable_time`: intervals covered by non-stale source observations.
- `uptime`: available or in-use observable duration / observable duration.
- `outage_frequency`: complete outage transitions per observable period.
- `MTTR`: arithmetic mean complete-outage duration.
- `median_outage_duration`: median completed outage duration.

Stale intervals are excluded and reported separately.

## Probability of a free connector

Introduced in Phase 4:

```text
p_free = (successes + alpha) / (samples + alpha + beta)
```

Success means at least one operational connector was observed available in the matching weekday/time bucket. Priors are derived from a documented regional peer group. The UI reports sample size, observable coverage, freshness, and interval confidence. It does not predict queues or waiting time.

## Timestamps

- `source_observed_at`: source's event/snapshot time.
- `ingested_at`: backend receipt time.
- `bucket_start`: exact UTC ten-minute boundary.
- UI display zone: `Europe/Berlin`.

