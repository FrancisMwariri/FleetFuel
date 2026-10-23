import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../app_theme.dart';
import '../data/app_controller.dart';
import '../data/models.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({
    super.key,
    required this.controller,
    required this.onLogFuel,
    required this.onOpenPurchase,
  });

  final AppController controller;
  final VoidCallback onLogFuel;
  final ValueChanged<FuelPurchase> onOpenPurchase;

  String get _greeting {
    final hour = DateTime.now().hour;
    if (hour < 12) return 'Good morning,';
    if (hour < 17) return 'Good afternoon,';
    return 'Good evening,';
  }

  @override
  Widget build(BuildContext context) {
    final user = controller.user;
    final summary = controller.summary;
    final recent = controller.purchases.toList()
      ..sort((a, b) => b.purchasedAt.compareTo(a.purchasedAt));
    final money = NumberFormat('#,##0.00');
    return RefreshIndicator(
      onRefresh: controller.refresh,
      child: CustomScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          SliverToBoxAdapter(
            child: Container(
              color: MediFuelColors.navy,
              padding: const EdgeInsets.fromLTRB(24, 22, 20, 24),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _greeting,
                          style: const TextStyle(
                            color: Colors.white70,
                            fontSize: 14,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          user?.fullName ?? 'Fleet manager',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 25,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'Keep your ambulances ready and moving.',
                          style: TextStyle(color: Colors.white70, fontSize: 13),
                        ),
                      ],
                    ),
                  ),
                  IconButton.filledTonal(
                    tooltip: 'Refresh fleet data',
                    onPressed: controller.busy ? null : controller.refresh,
                    style: IconButton.styleFrom(
                      backgroundColor: Colors.white.withValues(alpha: .13),
                      foregroundColor: Colors.white,
                    ),
                    icon: const Icon(Icons.refresh),
                  ),
                ],
              ),
            ),
          ),
          if (controller.error != null)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
                child: _Notice(
                  text: controller.error!,
                  color: MediFuelColors.amber,
                  icon: Icons.info_outline,
                ),
              ),
            ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 22, 20, 24),
            sliver: SliverList.list(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        'Fleet overview',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ),
                    const Text(
                      'All records',
                      style: TextStyle(
                        color: MediFuelColors.muted,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                GridView.count(
                  crossAxisCount: 2,
                  mainAxisSpacing: 10,
                  crossAxisSpacing: 10,
                  childAspectRatio: 1.55,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  children: [
                    _MetricTile(
                      icon: Icons.local_shipping_outlined,
                      label: 'Vehicles',
                      value: '${summary.vehicleCount}',
                      accent: MediFuelColors.navy,
                    ),
                    _MetricTile(
                      icon: Icons.local_gas_station_outlined,
                      label: 'Fuel purchases',
                      value: '${summary.purchaseCount}',
                      accent: MediFuelColors.orange,
                    ),
                    _MetricTile(
                      icon: Icons.route_outlined,
                      label: 'Recorded distance',
                      value:
                          '${NumberFormat('#,##0').format(summary.distance)} km',
                      accent: MediFuelColors.blue,
                    ),
                    _MetricTile(
                      icon: Icons.payments_outlined,
                      label: 'Recorded spend',
                      value:
                          '${summary.currency ?? controller.currency} ${money.format(summary.totalAmount)}',
                      accent: MediFuelColors.green,
                    ),
                  ],
                ),
                const SizedBox(height: 22),
                if (controller.openAlerts.isNotEmpty) ...[
                  _SectionTitle(
                    title: 'Needs attention',
                    trailing: '${controller.openAlerts.length} open',
                  ),
                  const SizedBox(height: 10),
                  ...controller.openAlerts
                      .take(2)
                      .map(
                        (alert) => Padding(
                          padding: const EdgeInsets.only(bottom: 9),
                          child: _AlertTile(alert: alert),
                        ),
                      ),
                  const SizedBox(height: 14),
                ],
                _SectionTitle(
                  title: 'Recent activity',
                  trailing: 'Most recent',
                ),
                const SizedBox(height: 10),
                if (recent.isEmpty)
                  const _EmptySection(
                    icon: Icons.local_gas_station_outlined,
                    title: 'No fuel entries yet',
                    subtitle:
                        'Log the next refuel to start your fleet history.',
                  )
                else
                  _ActivityList(
                    purchases: recent.take(5).toList(),
                    vehicles: controller.vehicles,
                    onOpenPurchase: onOpenPurchase,
                  ),
                const SizedBox(height: 18),
                FilledButton.icon(
                  onPressed: onLogFuel,
                  icon: const Icon(Icons.add),
                  label: const Text('Log fuel entry'),
                  style: FilledButton.styleFrom(
                    backgroundColor: MediFuelColors.orange,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 15),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _MetricTile extends StatelessWidget {
  const _MetricTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.accent,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color accent;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(13),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Icon(icon, size: 21, color: accent),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                value,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: MediFuelColors.ink,
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: MediFuelColors.muted,
                  fontSize: 11,
                ),
              ),
            ],
          ),
        ],
      ),
    ),
  );
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title, required this.trailing});

  final String title;
  final String trailing;

  @override
  Widget build(BuildContext context) => Row(
    children: [
      Expanded(
        child: Text(title, style: Theme.of(context).textTheme.titleLarge),
      ),
      Text(
        trailing,
        style: const TextStyle(color: MediFuelColors.muted, fontSize: 12),
      ),
    ],
  );
}

class _AlertTile extends StatelessWidget {
  const _AlertTile({required this.alert});

  final Map<String, dynamic> alert;

  @override
  Widget build(BuildContext context) => Card(
    color: const Color(0xFFFFF6EA),
    child: Padding(
      padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          const Icon(Icons.warning_amber_rounded, color: MediFuelColors.orange),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              '${alert['reason'] ?? 'Review this purchase pattern.'}',
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: MediFuelColors.ink,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          const Icon(Icons.chevron_right, color: MediFuelColors.muted),
        ],
      ),
    ),
  );
}

class _ActivityList extends StatelessWidget {
  const _ActivityList({
    required this.purchases,
    required this.vehicles,
    required this.onOpenPurchase,
  });

  final List<FuelPurchase> purchases;
  final List<FleetVehicle> vehicles;
  final ValueChanged<FuelPurchase> onOpenPurchase;

  @override
  Widget build(BuildContext context) => Card(
    clipBehavior: Clip.antiAlias,
    child: Column(
      children: [
        for (var index = 0; index < purchases.length; index++) ...[
          if (index > 0) const Divider(height: 1, indent: 54),
          _ActivityRow(
            purchase: purchases[index],
            vehicles: vehicles,
            onTap: () => onOpenPurchase(purchases[index]),
          ),
        ],
      ],
    ),
  );
}

class _ActivityRow extends StatelessWidget {
  const _ActivityRow({
    required this.purchase,
    required this.vehicles,
    required this.onTap,
  });

  final FuelPurchase purchase;
  final List<FleetVehicle> vehicles;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final vehicle = vehicles
        .where((item) => item.id == purchase.vehicleId)
        .firstOrNull;
    return ListTile(
      onTap: onTap,
      leading: CircleAvatar(
        backgroundColor: const Color(0xFFFCEBDD),
        foregroundColor: MediFuelColors.orange,
        child: const Icon(Icons.local_gas_station_outlined, size: 20),
      ),
      title: Text(
        vehicle?.registration ?? 'Fleet vehicle',
        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
      ),
      subtitle: Text(
        'Refueled · ${DateFormat('d MMM yyyy').format(purchase.purchasedAt)}',
      ),
      trailing: Text(
        '${purchase.litres.toStringAsFixed(0)} L',
        style: const TextStyle(fontWeight: FontWeight.w700),
      ),
    );
  }
}

class _EmptySection extends StatelessWidget {
  const _EmptySection({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  final IconData icon;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Row(
        children: [
          Icon(icon, color: MediFuelColors.navy, size: 28),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 3),
                Text(subtitle),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}

class _Notice extends StatelessWidget {
  const _Notice({required this.text, required this.color, required this.icon});

  final String text;
  final Color color;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(13),
    decoration: BoxDecoration(
      color: color,
      borderRadius: BorderRadius.circular(14),
    ),
    child: Row(
      children: [
        Icon(icon, size: 18, color: MediFuelColors.navy),
        const SizedBox(width: 9),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(color: MediFuelColors.ink, fontSize: 12),
          ),
        ),
      ],
    ),
  );
}
