import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../app_theme.dart';
import '../data/api_client.dart';
import '../data/app_controller.dart';
import '../data/models.dart';

class EntryDetailsScreen extends StatefulWidget {
  const EntryDetailsScreen({
    super.key,
    required this.controller,
    required this.purchase,
    required this.registration,
    required this.vehicleTitle,
  });

  final AppController controller;
  final FuelPurchase purchase;
  final String registration;
  final String vehicleTitle;

  @override
  State<EntryDetailsScreen> createState() => _EntryDetailsScreenState();
}

class _EntryDetailsScreenState extends State<EntryDetailsScreen> {
  late final Future<List<Map<String, dynamic>>> _attachments = widget
      .controller
      .api
      .attachments(widget.purchase.id);

  @override
  Widget build(BuildContext context) {
    final purchase = widget.purchase;
    final dateTime = DateFormat('d MMM yyyy, h:mm a');
    return Scaffold(
      appBar: AppBar(title: const Text('Entry details')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  const CircleAvatar(
                    backgroundColor: Color(0xFFEAF0F8),
                    foregroundColor: MediFuelColors.navy,
                    child: Icon(Icons.directions_car_outlined),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.registration,
                          style: const TextStyle(fontWeight: FontWeight.w800),
                        ),
                        if (widget.vehicleTitle.isNotEmpty)
                          Text(
                            widget.vehicleTitle,
                            style: const TextStyle(color: MediFuelColors.muted),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            clipBehavior: Clip.antiAlias,
            child: Column(
              children: [
                _DetailRow(
                  label: 'Date',
                  value: dateTime.format(purchase.purchasedAt),
                ),
                _DetailRow(
                  label: 'Fuel type',
                  value: _fuelLabel(purchase.fuelType),
                ),
                _DetailRow(
                  label: 'Litres purchased',
                  value: '${_formatNumber(purchase.litres)} L',
                ),
                _DetailRow(
                  label: 'Price per litre',
                  value:
                      '${purchase.currency} ${_formatNumber(purchase.pricePerLitre)}',
                ),
                _DetailRow(
                  label: 'Odometer',
                  value: '${_formatNumber(purchase.odometer)} km',
                ),
                if (purchase.station?.isNotEmpty == true)
                  _DetailRow(label: 'Fuel station', value: purchase.station!),
                Container(
                  width: double.infinity,
                  color: MediFuelColors.navy,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 15,
                  ),
                  child: Row(
                    children: [
                      const Text(
                        'Total cost',
                        style: TextStyle(color: Colors.white),
                      ),
                      const Spacer(),
                      Text(
                        '${purchase.currency} ${_formatNumber(purchase.total)}',
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w800,
                          fontSize: 18,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Submitted by',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      CircleAvatar(
                        backgroundColor: MediFuelColors.navy,
                        child: Text(
                          _initials(widget.controller.user?.fullName ?? 'MF'),
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          purchase.submittedById == widget.controller.user?.id
                              ? '${widget.controller.user?.fullName ?? 'You'} (you)'
                              : 'Fleet member',
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ),
                      Text(
                        DateFormat('d MMM').format(purchase.purchasedAt),
                        style: const TextStyle(
                          color: MediFuelColors.muted,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          Text('Attachments', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 9),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _attachments,
            builder: (context, snapshot) {
              if (snapshot.hasError) {
                return _AttachmentMessage(
                  text: snapshot.error is ApiException
                      ? (snapshot.error! as ApiException).message
                      : 'Attachments could not be loaded.',
                  icon: Icons.error_outline,
                );
              }
              if (!snapshot.hasData) {
                return const Padding(
                  padding: EdgeInsets.all(20),
                  child: Center(child: CircularProgressIndicator()),
                );
              }
              final attachments = snapshot.data!;
              if (attachments.isEmpty) {
                return const _AttachmentMessage(
                  text: 'No receipt or odometer photos were attached.',
                  icon: Icons.photo_library_outlined,
                );
              }
              return Column(
                children: attachments
                    .map(
                      (attachment) => Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: _AttachmentCard(
                          controller: widget.controller,
                          recordId: purchase.id,
                          attachment: attachment,
                        ),
                      ),
                    )
                    .toList(),
              );
            },
          ),
          const SizedBox(height: 8),
          const Text(
            'Purchase litres are recorded transaction data; they are not a measurement of fuel consumed.',
            style: TextStyle(color: MediFuelColors.muted, fontSize: 12),
          ),
        ],
      ),
    );
  }

  String _fuelLabel(String value) => switch (value) {
    'DIESEL' => 'Diesel',
    'PETROL' || 'GASOLINE' => 'Petrol',
    'ELECTRIC' => 'Electric',
    _ => 'Other',
  };

  String _formatNumber(num value) => NumberFormat('#,##0.##').format(value);

  String _initials(String name) => name
      .trim()
      .split(RegExp(r'\s+'))
      .take(2)
      .where((part) => part.isNotEmpty)
      .map((part) => part[0])
      .join()
      .toUpperCase();
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
    child: Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: const TextStyle(color: MediFuelColors.muted),
          ),
        ),
        const SizedBox(width: 12),
        Flexible(
          child: Text(
            value,
            textAlign: TextAlign.end,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
      ],
    ),
  );
}

class _AttachmentCard extends StatefulWidget {
  const _AttachmentCard({
    required this.controller,
    required this.recordId,
    required this.attachment,
  });

  final AppController controller;
  final String recordId;
  final Map<String, dynamic> attachment;

  @override
  State<_AttachmentCard> createState() => _AttachmentCardState();
}

class _AttachmentCardState extends State<_AttachmentCard> {
  late final Future<Uint8List> _image = widget.controller.api
      .downloadAttachment(widget.recordId, widget.attachment['id'] as String);

  @override
  Widget build(BuildContext context) {
    final kind = widget.attachment['kind'] as String? ?? '';
    return Card(
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
            child: Text(
              kind == 'RECEIPT' ? 'Fuel receipt' : 'Odometer',
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
          ),
          FutureBuilder<Uint8List>(
            future: _image,
            builder: (context, snapshot) {
              if (snapshot.hasError) {
                return const _AttachmentMessage(
                  text: 'This image could not be loaded.',
                  icon: Icons.broken_image_outlined,
                );
              }
              if (!snapshot.hasData) {
                return const SizedBox(
                  height: 150,
                  child: Center(child: CircularProgressIndicator()),
                );
              }
              return Image.memory(
                snapshot.data!,
                width: double.infinity,
                height: 220,
                fit: BoxFit.contain,
                errorBuilder: (context, error, stackTrace) =>
                    const _AttachmentMessage(
                      text: 'This image could not be displayed.',
                      icon: Icons.broken_image_outlined,
                    ),
              );
            },
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 8, 14, 12),
            child: Text(
              '${_formatBytes((widget.attachment['size_bytes'] as num?)?.toInt() ?? 0)} · ${DateFormat('d MMM yyyy').format(DateTime.parse(widget.attachment['created_at'] as String).toLocal())}',
              style: const TextStyle(color: MediFuelColors.muted, fontSize: 11),
            ),
          ),
        ],
      ),
    );
  }

  String _formatBytes(int bytes) => bytes < 1024
      ? '$bytes B'
      : bytes < 1024 * 1024
      ? '${(bytes / 1024).toStringAsFixed(0)} KB'
      : '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
}

class _AttachmentMessage extends StatelessWidget {
  const _AttachmentMessage({required this.text, required this.icon});

  final String text;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(18),
    child: Row(
      children: [
        Icon(icon, color: MediFuelColors.muted),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(color: MediFuelColors.muted),
          ),
        ),
      ],
    ),
  );
}
