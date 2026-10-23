import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../app_theme.dart';
import '../data/app_controller.dart';
import '../data/models.dart';

class VehiclesScreen extends StatefulWidget {
  const VehiclesScreen({super.key, required this.controller});

  final AppController controller;

  @override
  State<VehiclesScreen> createState() => _VehiclesScreenState();
}

class _VehiclesScreenState extends State<VehiclesScreen> {
  String _filter = 'All';
  String _search = '';

  List<FleetVehicle> get _visible {
    final query = _search.trim().toLowerCase();
    return widget.controller.vehicles.where((vehicle) {
      final matchesText = query.isEmpty ||
          vehicle.registration.toLowerCase().contains(query) ||
          (vehicle.title).toLowerCase().contains(query) ||
          (vehicle.fleetIdentifier ?? '').toLowerCase().contains(query);
      final matchesFilter = switch (_filter) {
        'In service' => vehicle.status == 'ACTIVE',
        'Inactive' => vehicle.status != 'ACTIVE',
        _ => true,
      };
      return matchesText && matchesFilter;
    }).toList();
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: widget.controller.refresh,
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverToBoxAdapter(
              child: Container(
                color: MediFuelColors.navy,
                padding: const EdgeInsets.fromLTRB(22, 20, 22, 22),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('My vehicles', style: Theme.of(context).textTheme.headlineLarge?.copyWith(color: Colors.white)),
                    const SizedBox(height: 15),
                    TextField(
                      onChanged: (value) => setState(() => _search = value),
                      style: const TextStyle(color: MediFuelColors.ink),
                      decoration: const InputDecoration(
                        prefixIcon: Icon(Icons.search),
                        hintText: 'Search registration or fleet ID',
                      ),
                    ),
                  ],
                ),
              ),
            ),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(18, 14, 18, 8),
                child: Wrap(
                  spacing: 8,
                  children: [
                    for (final filter in ['All', 'In service', 'Inactive'])
                      ChoiceChip(
                        label: Text(filter),
                        selected: _filter == filter,
                        onSelected: (_) => setState(() => _filter = filter),
                      ),
                  ],
                ),
              ),
            ),
            if (_visible.isEmpty)
              SliverFillRemaining(
                hasScrollBody: false,
                child: Center(
                  child: Padding(
                    padding: const EdgeInsets.all(32),
                    child: Text(
                      widget.controller.vehicles.isEmpty ? 'No vehicles are assigned to this fleet yet.' : 'No vehicles match this search.',
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
              )
            else
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 28),
                sliver: SliverList.separated(
                  itemCount: _visible.length,
                  separatorBuilder: (context, index) => const SizedBox(height: 10),
                  itemBuilder: (context, index) => _VehicleTile(vehicle: _visible[index]),
                ),
              ),
          ],
        ),
      );
}

class _VehicleTile extends StatelessWidget {
  const _VehicleTile({required this.vehicle});

  final FleetVehicle vehicle;

  @override
  Widget build(BuildContext context) {
    final inactive = vehicle.status != 'ACTIVE';
    final last = vehicle.lastPurchase;
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 14),
        child: Row(
          children: [
            Container(
              width: 45,
              height: 45,
              decoration: BoxDecoration(color: const Color(0xFFEAF0F8), borderRadius: BorderRadius.circular(13)),
              child: const Icon(Icons.local_shipping_outlined, color: MediFuelColors.navy),
            ),
            const SizedBox(width: 13),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: 7,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Text(vehicle.registration, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14)),
                      if (inactive) _StatusPill(status: vehicle.status),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(vehicle.title.isEmpty ? vehicle.fuelType : vehicle.title, style: const TextStyle(fontSize: 12, color: MediFuelColors.muted)),
                  const SizedBox(height: 4),
                  Text(
                    last == null
                        ? 'No fuel entries yet'
                        : 'Last refuel ${DateFormat('d MMM').format(last.purchasedAt)} · ${NumberFormat('#,##0').format(last.odometer)} km',
                    style: const TextStyle(fontSize: 11, color: MediFuelColors.muted),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: MediFuelColors.muted),
          ],
        ),
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: MediFuelColors.amber, borderRadius: BorderRadius.circular(8)),
        child: Text(status.replaceAll('_', ' ').toLowerCase(), style: const TextStyle(color: MediFuelColors.ink, fontSize: 10, fontWeight: FontWeight.w700)),
      );
}