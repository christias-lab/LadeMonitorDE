# LadePulse DE mobile

Android-first Flutter client for the deterministic Phase 1 observability API.
The app uses Material 3, Riverpod, go_router, Dio, MapLibre, and explicit
`Europe/Berlin` display-time conversion.

From this directory:

```bash
flutter pub get
flutter analyze
flutter test
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

`10.0.2.2` reaches the development host from the standard Android emulator.
Pass a reachable host address for other devices. Provider credentials and
source-system endpoints never belong in this client.
