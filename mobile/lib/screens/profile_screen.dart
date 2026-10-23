import 'package:flutter/material.dart';

import '../app_theme.dart';
import '../data/app_controller.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key, required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) {
    final user = controller.user;
    final initials = (user?.fullName.trim().split(RegExp(r'\s+')).take(2).map((part) => part.isEmpty ? '' : part[0]).join() ?? 'MF').toUpperCase();
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
      children: [
        Text('Profile', style: Theme.of(context).textTheme.headlineLarge),
        const SizedBox(height: 18),
        Card(
          color: MediFuelColors.navy,
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Row(
              children: [
                CircleAvatar(radius: 28, backgroundColor: Colors.white, foregroundColor: MediFuelColors.navy, child: Text(initials, style: const TextStyle(fontWeight: FontWeight.w800))),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(user?.fullName ?? '', style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w800)),
                      const SizedBox(height: 3),
                      Text(user?.email ?? '', style: const TextStyle(color: Colors.white70, fontSize: 12)),
                      const SizedBox(height: 8),
                      Text(user?.role.replaceAll('_', ' ').toLowerCase() ?? '', style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700)),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 18),
        const _ProfileSection(children: [
          _ProfileRow(icon: Icons.badge_outlined, label: 'Account information'),
          _ProfileRow(icon: Icons.lock_outline, label: 'Change password'),
          _ProfileRow(icon: Icons.notifications_none, label: 'Notifications'),
        ]),
        const SizedBox(height: 14),
        const _ProfileSection(children: [
          _ProfileRow(icon: Icons.help_outline, label: 'Help & support'),
          _ProfileRow(icon: Icons.info_outline, label: 'About MediFuel', detail: 'v1.0.0'),
        ]),
        const SizedBox(height: 24),
        OutlinedButton.icon(
          onPressed: () async {
            await controller.logout();
          },
          icon: const Icon(Icons.logout),
          label: const Text('Log out'),
          style: OutlinedButton.styleFrom(foregroundColor: MediFuelColors.red, padding: const EdgeInsets.symmetric(vertical: 14)),
        ),
      ],
    );
  }
}

class _ProfileSection extends StatelessWidget {
  const _ProfileSection({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Card(
        clipBehavior: Clip.antiAlias,
        child: Column(children: [
          for (var index = 0; index < children.length; index++) ...[
            if (index > 0) const Divider(height: 1, indent: 48),
            children[index],
          ],
        ]),
      );
}

class _ProfileRow extends StatelessWidget {
  const _ProfileRow({required this.icon, required this.label, this.detail});

  final IconData icon;
  final String label;
  final String? detail;

  @override
  Widget build(BuildContext context) => ListTile(
        leading: Icon(icon, color: MediFuelColors.navy),
        title: Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
        trailing: detail == null ? const Icon(Icons.chevron_right, color: MediFuelColors.muted) : Text(detail!, style: const TextStyle(color: MediFuelColors.muted)),
        onTap: detail == null ? () => ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('This account setting is not available yet.'))) : null,
      );
}