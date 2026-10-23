// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:medifuel_mobile/data/api_client.dart';
import 'package:medifuel_mobile/data/app_controller.dart';
import 'package:medifuel_mobile/data/local_store.dart';
import 'package:medifuel_mobile/data/models.dart';
import 'package:medifuel_mobile/main.dart';
import 'package:medifuel_mobile/screens/entry_details_screen.dart';

void main() {
  testWidgets('shows the MediFuel sign-in screen when no user is signed in', (
    tester,
  ) async {
    final controller = AppController(
      api: ApiClient(
        baseUrl: 'http://localhost/api/v1',
        client: MockClient((_) async => throw StateError('Unexpected request')),
      ),
      store: LocalStore(),
    )..initialized = true;

    await tester.pumpWidget(MediFuelApp(controller: controller));

    expect(find.text('Sign in to your account'), findsOneWidget);
    expect(find.text('Log in'), findsOneWidget);
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is RichText && widget.text.toPlainText() == 'MediFuel',
      ),
      findsOneWidget,
    );

    controller.api.close();
  });

  testWidgets('shows recorded fuel details and an empty attachments state', (
    tester,
  ) async {
    final controller =
        AppController(
            api: ApiClient(
              baseUrl: 'http://localhost/api/v1',
              client: MockClient((request) async {
                expect(
                  request.url.path,
                  '/api/v1/fuel-records/record-1/attachments',
                );
                return http.Response('[]', 200);
              }),
            )..token = 'access-token',
            store: LocalStore(),
          )
          ..user = const AppUser(
            id: 'user-1',
            email: 'driver@example.com',
            fullName: 'Test Driver',
            role: 'DRIVER',
            organizationId: 'org-1',
          );
    final purchase = FuelPurchase(
      id: 'record-1',
      vehicleId: 'vehicle-1',
      odometer: 12450,
      litres: 50,
      total: 9000,
      pricePerLitre: 180,
      currency: 'KES',
      fuelType: 'DIESEL',
      purchasedAt: DateTime(2026, 10, 12, 10, 24),
      source: 'ONLINE',
      submittedById: 'user-1',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: EntryDetailsScreen(
          controller: controller,
          purchase: purchase,
          registration: 'KCE 001A',
          vehicleTitle: 'Toyota Hilux',
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('No receipt or odometer photos were attached.'),
      250,
      scrollable: find.byType(Scrollable).first,
    );

    expect(find.text('Entry details'), findsOneWidget);
    expect(find.text('KES 9,000'), findsOneWidget);
    expect(find.text('12,450 km'), findsOneWidget);
    expect(
      find.text('No receipt or odometer photos were attached.'),
      findsOneWidget,
    );
    expect(
      find.text(
        'Purchase litres are recorded transaction data; they are not a measurement of fuel consumed.',
      ),
      findsOneWidget,
    );
    controller.api.close();
  });
}
