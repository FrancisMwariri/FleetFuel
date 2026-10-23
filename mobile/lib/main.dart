import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import 'app_theme.dart';
import 'data/api_client.dart';
import 'data/app_controller.dart';
import 'data/local_store.dart';
import 'screens/app_root.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final controller = AppController(
    api: ApiClient(baseUrl: _apiBaseUrl()),
    store: LocalStore(),
  );
  await controller.initialize();
  runApp(MediFuelApp(controller: controller));
}

String _apiBaseUrl() {
  const configured = String.fromEnvironment('MEDIFUEL_API_BASE_URL');
  if (configured.isNotEmpty) return configured;
  if (kDebugMode) {
    if (kIsWeb) return 'http://${Uri.base.host}:8000/api/v1';
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000/api/v1';
    }
    return 'http://localhost:8000/api/v1';
  }
  return 'https://fleetfuel-api.onrender.com/api/v1';
}

class MediFuelApp extends StatelessWidget {
  const MediFuelApp({super.key, required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'MediFuel',
    debugShowCheckedModeBanner: false,
    theme: buildMediFuelTheme(),
    home: AppRoot(controller: controller),
  );
}
