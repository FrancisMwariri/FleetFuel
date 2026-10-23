import 'dart:convert';

class AppUser {
  const AppUser({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
    this.organizationId,
  });

  final String id;
  final String email;
  final String fullName;
  final String role;
  final String? organizationId;

  Map<String, dynamic> toJson() => {
    'id': id,
    'email': email,
    'full_name': fullName,
    'role': role,
    'organization_id': organizationId,
  };

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
    id: json['id'] as String,
    email: json['email'] as String,
    fullName: json['full_name'] as String,
    role: json['role'] as String,
    organizationId: json['organization_id'] as String?,
  );
}

class FleetVehicle {
  const FleetVehicle({
    required this.id,
    required this.registration,
    required this.fuelType,
    required this.status,
    this.fleetIdentifier,
    this.make,
    this.model,
    this.lastOdometer,
    this.lastPurchase,
  });

  final String id;
  final String registration;
  final String fuelType;
  final String status;
  final String? fleetIdentifier;
  final String? make;
  final String? model;
  final int? lastOdometer;
  final FuelPurchase? lastPurchase;

  String get title => [
    make,
    model,
  ].whereType<String>().where((value) => value.isNotEmpty).join(' ');

  factory FleetVehicle.fromJson(Map<String, dynamic> json) => FleetVehicle(
    id: json['id'] as String,
    registration: json['registration_number'] as String,
    fuelType: json['fuel_type'] as String,
    status: json['status'] as String? ?? 'ACTIVE',
    fleetIdentifier: json['fleet_identifier'] as String?,
    make: json['make'] as String?,
    model: json['model'] as String?,
  );

  FleetVehicle withHistory(List<FuelPurchase> purchases) {
    final forVehicle = purchases.where((item) => item.vehicleId == id).toList()
      ..sort((a, b) => b.purchasedAt.compareTo(a.purchasedAt));
    if (forVehicle.isEmpty) return this;
    return FleetVehicle(
      id: id,
      registration: registration,
      fuelType: fuelType,
      status: status,
      fleetIdentifier: fleetIdentifier,
      make: make,
      model: model,
      lastOdometer: forVehicle.first.odometer,
      lastPurchase: forVehicle.first,
    );
  }
}

class FuelPurchase {
  const FuelPurchase({
    required this.id,
    required this.vehicleId,
    required this.odometer,
    required this.litres,
    required this.total,
    required this.pricePerLitre,
    required this.currency,
    required this.fuelType,
    required this.purchasedAt,
    required this.source,
    required this.submittedById,
    this.station,
  });

  final String id;
  final String vehicleId;
  final int odometer;
  final double litres;
  final double total;
  final double pricePerLitre;
  final String currency;
  final String fuelType;
  final DateTime purchasedAt;
  final String source;
  final String submittedById;
  final String? station;

  factory FuelPurchase.fromJson(Map<String, dynamic> json) => FuelPurchase(
    id: json['id'] as String,
    vehicleId: json['vehicle_id'] as String,
    odometer: (json['odometer_reading'] as num).toInt(),
    litres: (json['litres_purchased'] as num).toDouble(),
    total: (json['total_amount'] as num).toDouble(),
    pricePerLitre: (json['price_per_litre'] as num).toDouble(),
    currency: json['currency'] as String,
    fuelType: json['fuel_type'] as String,
    purchasedAt: DateTime.parse(json['purchased_at'] as String).toLocal(),
    source: json['source'] as String? ?? 'ONLINE',
    submittedById: json['submitted_by_id'] as String,
    station: json['station_name'] as String?,
  );
}

class FleetSummary {
  const FleetSummary({
    this.vehicleCount = 0,
    this.activeVehicleCount = 0,
    this.openAlertCount = 0,
    this.purchaseCount = 0,
    this.totalAmount = 0,
    this.totalLitres = 0,
    this.currency = 'USD',
    this.distance = 0,
  });

  final int vehicleCount;
  final int activeVehicleCount;
  final int openAlertCount;
  final int purchaseCount;
  final double totalAmount;
  final double totalLitres;
  final String? currency;
  final int distance;

  factory FleetSummary.fromJson(Map<String, dynamic> json) => FleetSummary(
    vehicleCount: (json['vehicle_count'] as num?)?.toInt() ?? 0,
    activeVehicleCount: (json['active_vehicle_count'] as num?)?.toInt() ?? 0,
    openAlertCount: (json['open_alert_count'] as num?)?.toInt() ?? 0,
    purchaseCount: (json['purchase_count'] as num?)?.toInt() ?? 0,
    totalAmount: double.tryParse('${json['total_amount'] ?? 0}') ?? 0,
    totalLitres: double.tryParse('${json['total_litres_purchased'] ?? 0}') ?? 0,
    currency: json['currency'] as String?,
    distance:
        (json['distance_between_recorded_odometer_readings'] as num?)
            ?.toInt() ??
        0,
  );

  factory FleetSummary.forDriver({
    required List<FleetVehicle> vehicles,
    required List<FuelPurchase> purchases,
    required String currency,
  }) {
    final purchasesByVehicle = <String, List<FuelPurchase>>{};
    for (final purchase in purchases) {
      purchasesByVehicle
          .putIfAbsent(purchase.vehicleId, () => [])
          .add(purchase);
    }
    var distance = 0;
    for (final records in purchasesByVehicle.values) {
      records.sort((a, b) => a.purchasedAt.compareTo(b.purchasedAt));
      for (var index = 1; index < records.length; index++) {
        final interval = records[index].odometer - records[index - 1].odometer;
        if (interval >= 0) {
          distance += interval;
        }
      }
    }
    return FleetSummary(
      vehicleCount: vehicles.length,
      activeVehicleCount: vehicles
          .where((vehicle) => vehicle.status == 'ACTIVE')
          .length,
      purchaseCount: purchases.length,
      totalAmount: purchases.fold(
        0,
        (total, purchase) => total + purchase.total,
      ),
      totalLitres: purchases.fold(
        0,
        (total, purchase) => total + purchase.litres,
      ),
      currency: currency,
      distance: distance,
    );
  }
}

class PendingFuelEntry {
  const PendingFuelEntry({
    required this.localId,
    required this.record,
    required this.attachments,
    this.error,
  });

  final String localId;
  final Map<String, dynamic> record;
  final List<Map<String, String>> attachments;
  final String? error;

  PendingFuelEntry withError(String? message) => PendingFuelEntry(
    localId: localId,
    record: record,
    attachments: attachments,
    error: message,
  );

  Map<String, dynamic> toJson() => {
    'local_id': localId,
    'record': record,
    'attachments': attachments,
    'error': error,
  };

  factory PendingFuelEntry.fromJson(Map<String, dynamic> json) =>
      PendingFuelEntry(
        localId: json['local_id'] as String,
        record: Map<String, dynamic>.from(json['record'] as Map),
        attachments: (json['attachments'] as List<dynamic>? ?? const [])
            .map((item) => Map<String, String>.from(item as Map))
            .toList(),
        error: json['error'] as String?,
      );

  String encode() => jsonEncode(toJson());
}
