import 'package:flutter_test/flutter_test.dart';
import 'package:medifuel_mobile/data/models.dart';

void main() {
  test('builds a driver summary from assigned vehicles and own records', () {
    final vehicles = [
      const FleetVehicle(
        id: 'vehicle-1',
        registration: 'KCE 001A',
        fuelType: 'DIESEL',
        status: 'ACTIVE',
      ),
      const FleetVehicle(
        id: 'vehicle-2',
        registration: 'KCE 002A',
        fuelType: 'DIESEL',
        status: 'INACTIVE',
      ),
    ];
    final purchases = [
      _purchase(
        id: 'record-1',
        vehicleId: 'vehicle-1',
        odometer: 1000,
        litres: 40,
        total: 7000,
        day: 1,
      ),
      _purchase(
        id: 'record-2',
        vehicleId: 'vehicle-1',
        odometer: 1350,
        litres: 50,
        total: 9000,
        day: 2,
      ),
      _purchase(
        id: 'record-3',
        vehicleId: 'vehicle-2',
        odometer: 500,
        litres: 20,
        total: 3600,
        day: 3,
      ),
    ];

    final summary = FleetSummary.forDriver(
      vehicles: vehicles,
      purchases: purchases,
      currency: 'KES',
    );

    expect(summary.vehicleCount, 2);
    expect(summary.activeVehicleCount, 1);
    expect(summary.purchaseCount, 3);
    expect(summary.totalAmount, 19600);
    expect(summary.totalLitres, 110);
    expect(summary.currency, 'KES');
    expect(summary.distance, 350);
    expect(summary.openAlertCount, 0);
  });
}

FuelPurchase _purchase({
  required String id,
  required String vehicleId,
  required int odometer,
  required double litres,
  required double total,
  required int day,
}) => FuelPurchase(
  id: id,
  vehicleId: vehicleId,
  odometer: odometer,
  litres: litres,
  total: total,
  pricePerLitre: total / litres,
  currency: 'KES',
  fuelType: 'DIESEL',
  purchasedAt: DateTime(2026, 1, day),
  source: 'ONLINE',
  submittedById: 'driver-1',
);
