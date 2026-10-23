import 'package:flutter/material.dart';

import '../app_theme.dart';
import '../data/app_controller.dart';
import '../data/models.dart';
import 'dashboard_screen.dart';
import 'entry_details_screen.dart';
import 'fuel_entry_screen.dart';
import 'profile_screen.dart';
import 'reports_screen.dart';
import 'vehicles_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key, required this.controller});

  final AppController controller;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _selected = 0;

  Future<void> _openFuelEntry() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => FuelEntryScreen(controller: widget.controller),
      ),
    );
    await widget.controller.refresh();
  }

  Future<void> _openPurchase(FuelPurchase purchase) async {
    final vehicle = widget.controller.vehicles
        .where((item) => item.id == purchase.vehicleId)
        .firstOrNull;
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => EntryDetailsScreen(
          controller: widget.controller,
          purchase: purchase,
          registration: vehicle?.registration ?? 'Fleet vehicle',
          vehicleTitle: vehicle?.title ?? '',
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      DashboardScreen(
        controller: widget.controller,
        onLogFuel: _openFuelEntry,
        onOpenPurchase: (purchase) => _openPurchase(purchase),
      ),
      VehiclesScreen(controller: widget.controller),
      ReportsScreen(
        controller: widget.controller,
        onOpenPurchase: (purchase) => _openPurchase(purchase),
      ),
      ProfileScreen(controller: widget.controller),
    ];
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (context, _) => Scaffold(
        body: SafeArea(
          bottom: false,
          child: Column(
            children: [
              if (!widget.controller.online ||
                  widget.controller.pending.isNotEmpty)
                _SyncStrip(
                  controller: widget.controller,
                  onRetry: widget.controller.syncPending,
                ),
              Expanded(
                child: IndexedStack(index: _selected, children: pages),
              ),
            ],
          ),
        ),
        bottomNavigationBar: _BottomNav(
          selected: _selected,
          onSelect: (index) => setState(() => _selected = index),
          onLogFuel: _openFuelEntry,
        ),
      ),
    );
  }
}

class _SyncStrip extends StatelessWidget {
  const _SyncStrip({required this.controller, required this.onRetry});

  final AppController controller;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final offline = !controller.online;
    return Container(
      width: double.infinity,
      color: offline ? MediFuelColors.navyDeep : const Color(0xFFE9F4EE),
      padding: const EdgeInsets.fromLTRB(16, 9, 12, 9),
      child: Row(
        children: [
          Icon(
            offline ? Icons.wifi_off : Icons.sync,
            size: 18,
            color: offline ? Colors.white : MediFuelColors.green,
          ),
          const SizedBox(width: 9),
          Expanded(
            child: Text(
              offline
                  ? "You're offline · ${controller.pending.length} ${controller.pending.length == 1 ? 'entry' : 'entries'} saved on this device"
                  : '${controller.pending.length} entries waiting to sync',
              style: TextStyle(
                color: offline ? Colors.white : MediFuelColors.ink,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          TextButton(
            onPressed: offline || controller.busy ? null : onRetry,
            child: Text(
              offline ? 'Saved' : 'Sync now',
              style: TextStyle(
                color: offline ? Colors.white70 : MediFuelColors.navy,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _BottomNav extends StatelessWidget {
  const _BottomNav({
    required this.selected,
    required this.onSelect,
    required this.onLogFuel,
  });

  final int selected;
  final ValueChanged<int> onSelect;
  final VoidCallback onLogFuel;

  @override
  Widget build(BuildContext context) => Material(
    color: Colors.white,
    child: SafeArea(
      top: false,
      child: SizedBox(
        height: 68,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _NavItem(
              icon: Icons.home_outlined,
              active: Icons.home,
              label: 'Home',
              selected: selected == 0,
              onTap: () => onSelect(0),
            ),
            _NavItem(
              icon: Icons.directions_car_outlined,
              active: Icons.directions_car,
              label: 'Vehicles',
              selected: selected == 1,
              onTap: () => onSelect(1),
            ),
            SizedBox(
              width: 70,
              child: Transform.translate(
                offset: const Offset(0, -7),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SizedBox.square(
                      dimension: 48,
                      child: FloatingActionButton(
                        heroTag: 'log-fuel-nav',
                        elevation: 0,
                        backgroundColor: MediFuelColors.orange,
                        foregroundColor: Colors.white,
                        tooltip: 'Log fuel',
                        onPressed: onLogFuel,
                        child: const Icon(Icons.add, size: 27),
                      ),
                    ),
                    const SizedBox(height: 2),
                    const Text(
                      'Log fuel',
                      style: TextStyle(
                        fontSize: 10,
                        color: MediFuelColors.orange,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            _NavItem(
              icon: Icons.bar_chart_outlined,
              active: Icons.bar_chart,
              label: 'Reports',
              selected: selected == 2,
              onTap: () => onSelect(2),
            ),
            _NavItem(
              icon: Icons.person_outline,
              active: Icons.person,
              label: 'Profile',
              selected: selected == 3,
              onTap: () => onSelect(3),
            ),
          ],
        ),
      ),
    ),
  );
}

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.icon,
    required this.active,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final IconData active;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 66,
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            selected ? active : icon,
            size: 22,
            color: selected ? MediFuelColors.navy : MediFuelColors.muted,
          ),
          const SizedBox(height: 3),
          Text(
            label,
            style: TextStyle(
              fontSize: 10,
              color: selected ? MediFuelColors.navy : MediFuelColors.muted,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
            ),
          ),
        ],
      ),
    ),
  );
}
