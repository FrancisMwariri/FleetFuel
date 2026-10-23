import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../app_theme.dart';
import '../data/app_controller.dart';
import '../data/models.dart';

class ReportsScreen extends StatelessWidget {
  const ReportsScreen({
    super.key,
    required this.controller,
    required this.onOpenPurchase,
  });

  final AppController controller;
  final ValueChanged<FuelPurchase> onOpenPurchase;

  @override
  Widget build(BuildContext context) {
    final summary = controller.summary;
    final formatter = NumberFormat('#,##0.00');
    final topVehicles = controller.vehicles.map((vehicle) {
      final amount = controller.purchases
          .where((purchase) => purchase.vehicleId == vehicle.id)
          .fold<double>(0, (sum, purchase) => sum + purchase.litres);
      return (vehicle: vehicle, litres: amount);
    }).toList()..sort((a, b) => b.litres.compareTo(a.litres));
    final maxLitres = topVehicles.isEmpty ? 0.0 : topVehicles.first.litres;

    return RefreshIndicator(
      onRefresh: controller.refresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
        children: [
          Text('Reports', style: Theme.of(context).textTheme.headlineLarge),
          const SizedBox(height: 7),
          const Text(
            'Recorded purchases and odometer intervals. Purchase volume is not measured fuel consumption.',
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              Expanded(
                child: _ReportMetric(
                  label: 'Litres purchased',
                  value: '${formatter.format(summary.totalLitres)} L',
                  icon: Icons.local_gas_station_outlined,
                  color: MediFuelColors.orange,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _ReportMetric(
                  label: 'Recorded spend',
                  value:
                      '${summary.currency ?? controller.currency} ${formatter.format(summary.totalAmount)}',
                  icon: Icons.payments_outlined,
                  color: MediFuelColors.navy,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: _ReportMetric(
                  label: 'Recorded distance',
                  value: '${NumberFormat('#,##0').format(summary.distance)} km',
                  icon: Icons.route_outlined,
                  color: MediFuelColors.blue,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _ReportMetric(
                  label: 'Purchases',
                  value: '${summary.purchaseCount}',
                  icon: Icons.receipt_long_outlined,
                  color: MediFuelColors.green,
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Text(
            'Recorded purchases by vehicle',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          if (topVehicles.isEmpty)
            const _EmptyReport()
          else
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    for (final item in topVehicles) ...[
                      Row(
                        children: [
                          SizedBox(
                            width: 88,
                            child: Text(
                              item.vehicle.registration,
                              style: const TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                          Expanded(
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(5),
                              child: LinearProgressIndicator(
                                minHeight: 10,
                                value: maxLitres == 0
                                    ? 0
                                    : item.litres / maxLitres,
                                color: item == topVehicles.first
                                    ? MediFuelColors.orange
                                    : MediFuelColors.blue,
                                backgroundColor: const Color(0xFFE7EDF5),
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          SizedBox(
                            width: 42,
                            child: Text(
                              '${item.litres.toStringAsFixed(0)} L',
                              textAlign: TextAlign.end,
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),
                    ],
                    const Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        'Bars compare litres purchased per vehicle across the records loaded on this device.',
                        style: TextStyle(
                          fontSize: 11,
                          color: MediFuelColors.muted,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 20),
          Text(
            'Recent purchases',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 10),
          if (controller.purchases.isEmpty)
            const _EmptyReport()
          else
            Card(
              clipBehavior: Clip.antiAlias,
              child: Column(
                children: [
                  for (
                    var index = 0;
                    index < controller.purchases.take(8).length;
                    index++
                  ) ...[
                    if (index > 0) const Divider(height: 1, indent: 16),
                    _PurchaseRow(
                      purchase: controller.purchases[index],
                      onTap: () => onOpenPurchase(controller.purchases[index]),
                      registration:
                          controller.vehicles
                              .where(
                                (vehicle) =>
                                    vehicle.id ==
                                    controller.purchases[index].vehicleId,
                              )
                              .map((vehicle) => vehicle.registration)
                              .firstOrNull ??
                          'Vehicle',
                    ),
                  ],
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _ReportMetric extends StatelessWidget {
  const _ReportMetric({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color),
          const SizedBox(height: 12),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 3),
          Text(
            label,
            style: const TextStyle(fontSize: 11, color: MediFuelColors.muted),
          ),
        ],
      ),
    ),
  );
}

class _PurchaseRow extends StatelessWidget {
  const _PurchaseRow({
    required this.purchase,
    required this.registration,
    required this.onTap,
  });

  final FuelPurchase purchase;
  final String registration;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => ListTile(
    onTap: onTap,
    dense: true,
    title: Text(
      registration,
      style: const TextStyle(fontWeight: FontWeight.w700),
    ),
    subtitle: Text(DateFormat('d MMM yyyy').format(purchase.purchasedAt)),
    trailing: Text(
      '${purchase.litres.toStringAsFixed(0)} L',
      style: const TextStyle(fontWeight: FontWeight.w700),
    ),
  );
}

class _EmptyReport extends StatelessWidget {
  const _EmptyReport();

  @override
  Widget build(BuildContext context) => const Card(
    child: Padding(
      padding: EdgeInsets.all(20),
      child: Center(child: Text('No fuel records yet.')),
    ),
  );
}
