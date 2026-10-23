# MediFuel mobile

The Flutter client for MediFuel fleet users. It supports invitation-based
registration, sign-in, fleet dashboards, vehicle views, fuel entry and entry
details with receipt/odometer attachments, reports, and an offline queue that
synchronizes entries with the FleetFuel API.

## Development

From this directory, install dependencies and run the app:

```powershell
flutter pub get
flutter run
```

Debug builds use the local development API (`http://10.0.2.2:8000/api/v1` on
the Android emulator, the page host on port 8000 on web, and `localhost` on
other targets). Release builds default to the deployed API at
`https://fleetfuel-api.onrender.com/api/v1`. Set
`MEDIFUEL_API_BASE_URL` at build/run time to override either default, for
example `--dart-define=MEDIFUEL_API_BASE_URL=https://api.example.com/api/v1`.
The API must be reachable from the target device and configured to allow the
app's origin when running in a browser.

Run static analysis and tests with:

```powershell
flutter analyze
flutter test
```
