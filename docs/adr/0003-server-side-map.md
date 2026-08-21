# ADR 0003: Server-side bounded map delivery

Status: accepted

Every map request contains a bounding box, zoom, requested time, and filters. The API returns clusters at low zoom and capped individual features at high zoom. There is no endpoint that returns the full national connector inventory to mobile.

