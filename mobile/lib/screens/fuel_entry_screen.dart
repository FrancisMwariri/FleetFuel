import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';

import '../app_theme.dart';
import '../data/api_client.dart';
import '../data/app_controller.dart';
import '../data/models.dart';

class FuelEntryScreen extends StatefulWidget {
  const FuelEntryScreen({super.key, required this.controller});

  final AppController controller;

  @override
  State<FuelEntryScreen> createState() => _FuelEntryScreenState();
}

class _FuelEntryScreenState extends State<FuelEntryScreen> {
  final _formKey = GlobalKey<FormState>();
  final _litres = TextEditingController();
  final _price = TextEditingController();
  final _odometer = TextEditingController();
  final _station = TextEditingController();
  final _search = TextEditingController();
  final _picker = ImagePicker();

  int _step = 0;
  String? _vehicleId;
  String _fuelType = 'DIESEL';
  DateTime _purchasedAt = DateTime.now();
  final Map<String, Map<String, String>> _photos = {};
  bool _submitting = false;
  String? _error;

  FleetVehicle? get _vehicle => widget.controller.vehicles.where((item) => item.id == _vehicleId).firstOrNull;

  @override
  void dispose() {
    _litres.dispose();
    _price.dispose();
    _odometer.dispose();
    _station.dispose();
    _search.dispose();
    super.dispose();
  }

  double get _previewTotal {
    final litres = double.tryParse(_litres.text) ?? 0;
    final price = double.tryParse(_price.text) ?? 0;
    return litres * price;
  }

  Future<void> _chooseDate() async {
    final date = await showDatePicker(
      context: context,
      initialDate: _purchasedAt,
      firstDate: DateTime(2010),
      lastDate: DateTime.now(),
    );
    if (date != null) setState(() => _purchasedAt = date);
  }

  void _next() {
    if (_step == 0) {
      if (_vehicleId == null) {
        setState(() => _error = 'Select a vehicle to continue.');
        return;
      }
      setState(() {
        _step = 1;
        _error = null;
      });
      return;
    }
    if (_step == 1) {
      if (!_formKey.currentState!.validate()) return;
      setState(() {
        _step = 2;
        _error = null;
      });
      return;
    }
    if (_step == 2) {
      setState(() {
        _step = 3;
        _error = null;
      });
    }
  }

  void _back() {
    if (_step == 0) {
      Navigator.pop(context);
    } else {
      setState(() {
        _step--;
        _error = null;
      });
    }
  }

  Future<void> _pickPhoto(String kind, ImageSource source) async {
    final file = await _picker.pickImage(source: source, imageQuality: 82, maxWidth: 1800);
    if (file == null) return;
    final bytes = await file.readAsBytes();
    final extension = file.name.toLowerCase().split('.').last;
    final contentType = extension == 'png' ? 'image/png' : 'image/jpeg';
    setState(() {
      _photos[kind] = {
        'kind': kind,
        'filename': file.name.isEmpty ? '$kind.$extension' : file.name,
        'content_type': contentType,
        'bytes': base64Encode(bytes),
      };
    });
  }

  Future<void> _showPhotoSource(String kind) async {
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      builder: (context) => SafeArea(
        child: Wrap(
          children: [
            ListTile(leading: const Icon(Icons.photo_camera_outlined), title: const Text('Take photo'), onTap: () => Navigator.pop(context, ImageSource.camera)),
            ListTile(leading: const Icon(Icons.photo_library_outlined), title: const Text('Choose from gallery'), onTap: () => Navigator.pop(context, ImageSource.gallery)),
          ],
        ),
      ),
    );
    if (source != null) await _pickPhoto(kind, source);
  }

  Future<void> _submit() async {
    if (_vehicleId == null || !_formKey.currentState!.validate()) return;
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final queued = await widget.controller.saveFuelEntry(
        vehicleId: _vehicleId!,
        odometer: int.parse(_odometer.text.replaceAll(',', '')),
        fuelType: _fuelType,
        litres: _litres.text.trim(),
        pricePerLitre: _price.text.trim(),
        purchasedAt: _purchasedAt,
        station: _station.text,
        attachments: _photos.values.toList(),
      );
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (context) => AlertDialog(
          icon: Icon(queued ? Icons.sync : Icons.check_circle, color: queued ? MediFuelColors.orange : MediFuelColors.green, size: 38),
          title: Text(queued ? 'Saved on this device' : 'Entry submitted'),
          content: Text(queued
              ? 'The fuel entry is queued safely and will sync when the connection is back.'
              : 'Fuel and odometer data has been recorded by your fleet.'),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Done'),
            ),
          ],
        ),
      );
      if (mounted) Navigator.pop(context);
    } on ApiException catch (error) {
      setState(() => _error = error.message);
    } catch (_) {
      setState(() => _error = 'Could not save this entry on your device. Please try again.');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          leading: IconButton(tooltip: 'Back', onPressed: _back, icon: const Icon(Icons.arrow_back)),
          title: const Text('Add new data'),
          bottom: PreferredSize(
            preferredSize: const Size.fromHeight(46),
            child: _StepHeader(step: _step),
          ),
        ),
        body: Column(
          children: [
            Expanded(child: _stepContent()),
            _footer(),
          ],
        ),
      );

  Widget _stepContent() => switch (_step) {
        0 => _vehicleStep(),
        1 => _detailsStep(),
        2 => _photosStep(),
        _ => _reviewStep(),
      };

  Widget _vehicleStep() => ListView(
        padding: const EdgeInsets.fromLTRB(22, 22, 22, 20),
        children: [
          Text('Select vehicle', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 5),
          const Text('Choose the ambulance you are adding fuel data for.'),
          const SizedBox(height: 18),
          TextField(
            controller: _search,
            onChanged: (_) => setState(() {}),
            decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Search registration or fleet ID'),
          ),
          const SizedBox(height: 18),
          if (widget.controller.vehicles.isEmpty)
            const _StepEmpty(text: 'No vehicles are available for this account.')
          else
            ...widget.controller.vehicles.where((vehicle) {
              final query = _search.text.toLowerCase();
              return query.isEmpty || vehicle.registration.toLowerCase().contains(query) || (vehicle.fleetIdentifier ?? '').toLowerCase().contains(query);
            }).map((vehicle) => Padding(
                  padding: const EdgeInsets.only(bottom: 9),
                  child: _VehicleChoice(
                    vehicle: vehicle,
                    selected: _vehicleId == vehicle.id,
                    onTap: () => setState(() {
                      _vehicleId = vehicle.id;
                      _fuelType = vehicle.fuelType;
                      _error = null;
                    }),
                  ),
                )),
          if (_error != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_error!, style: const TextStyle(color: MediFuelColors.red))),
        ],
      );

  Widget _detailsStep() {
    final vehicle = _vehicle;
    return Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(22, 18, 22, 20),
        children: [
          _VehicleSummary(vehicle: vehicle),
          const SizedBox(height: 18),
          Row(
            children: [
              Expanded(
                child: InkWell(
                  onTap: _chooseDate,
                  borderRadius: BorderRadius.circular(14),
                  child: InputDecorator(
                    decoration: const InputDecoration(labelText: 'Fuel date', prefixIcon: Icon(Icons.calendar_today_outlined)),
                    child: Text(DateFormat('d MMM yyyy').format(_purchasedAt)),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: DropdownButtonFormField<String>(
                  initialValue: _fuelType,
                  decoration: const InputDecoration(labelText: 'Fuel type'),
                  items: ['DIESEL', 'PETROL', 'GASOLINE', 'OTHER']
                      .map((type) => DropdownMenuItem(value: type, child: Text(_fuelLabel(type))))
                      .toList(),
                  onChanged: (value) => setState(() => _fuelType = value ?? _fuelType),
                ),
              ),
            ],
          ),
          const SizedBox(height: 15),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: _litres,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  onChanged: (_) => setState(() {}),
                  decoration: const InputDecoration(labelText: 'Litres purchased', suffixText: 'L'),
                  validator: (value) => _positiveNumber(value, 'Enter litres greater than zero.'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextFormField(
                  controller: _price,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  onChanged: (_) => setState(() {}),
                  decoration: InputDecoration(labelText: 'Price per litre', suffixText: widget.controller.currency),
                  validator: (value) => _positiveNumber(value, 'Enter a price greater than zero.'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 15),
          TextFormField(
            controller: _odometer,
            keyboardType: TextInputType.number,
            decoration: InputDecoration(
              labelText: 'Odometer reading',
              suffixText: 'km',
              helperText: vehicle?.lastOdometer == null
                  ? 'Enter the current dashboard reading.'
                  : 'Last reading: ${NumberFormat('#,##0').format(vehicle!.lastOdometer)} km',
            ),
            validator: (value) {
              final entered = int.tryParse((value ?? '').replaceAll(',', ''));
              if (entered == null || entered < 0) return 'Enter a valid odometer reading.';
              if (vehicle?.lastOdometer != null && entered < vehicle!.lastOdometer!) {
                return 'Must be ${NumberFormat('#,##0').format(vehicle.lastOdometer)} km or higher.';
              }
              return null;
            },
          ),
          const SizedBox(height: 15),
          TextFormField(
            controller: _station,
            textCapitalization: TextCapitalization.words,
            decoration: const InputDecoration(labelText: 'Fuel station (optional)', prefixIcon: Icon(Icons.place_outlined)),
            maxLength: 160,
          ),
          const SizedBox(height: 4),
          _TotalPreview(total: _previewTotal, currency: widget.controller.currency),
          if (_error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(_error!, style: const TextStyle(color: MediFuelColors.red))),
        ],
      ),
    );
  }

  Widget _photosStep() => ListView(
        padding: const EdgeInsets.fromLTRB(22, 20, 22, 20),
        children: [
          Text('Photos', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 5),
          const Text('Add a receipt or odometer photo now, or attach it later.'),
          const SizedBox(height: 18),
          _PhotoCard(label: 'Fuel receipt', photo: _photos['RECEIPT'], onTap: () => _showPhotoSource('RECEIPT')),
          const SizedBox(height: 14),
          _PhotoCard(label: 'Odometer', photo: _photos['ODOMETER'], onTap: () => _showPhotoSource('ODOMETER')),
          if (_error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(_error!, style: const TextStyle(color: MediFuelColors.red))),
        ],
      );

  Widget _reviewStep() {
    final vehicle = _vehicle;
    return ListView(
      padding: const EdgeInsets.fromLTRB(22, 20, 22, 20),
      children: [
        Text('Review & confirm', style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 5),
        const Text('Check the details before submitting.'),
        const SizedBox(height: 18),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                _ReviewLine(label: 'Vehicle', value: '${vehicle?.registration ?? ''} ${vehicle?.title ?? ''}'),
                _ReviewLine(label: 'Fuel date', value: DateFormat('d MMM yyyy').format(_purchasedAt)),
                _ReviewLine(label: 'Fuel type', value: _fuelLabel(_fuelType)),
                _ReviewLine(label: 'Litres purchased', value: '${_litres.text} L'),
                _ReviewLine(label: 'Price per litre', value: '${widget.controller.currency} ${_price.text}'),
                _ReviewLine(label: 'Odometer', value: '${NumberFormat('#,##0').format(int.tryParse(_odometer.text.replaceAll(',', '')) ?? 0)} km'),
                const Divider(height: 20),
                Row(
                  children: [
                    const Text('Total cost', style: TextStyle(fontWeight: FontWeight.w700)),
                    const Spacer(),
                    Text('${widget.controller.currency} ${NumberFormat('#,##0.00').format(_previewTotal)}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17, color: MediFuelColors.navy)),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 14),
        Text('Photos · ${_photos.length} attached', style: const TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 8),
        for (final photo in _photos.values)
          ListTile(
            dense: true,
            leading: const Icon(Icons.attachment, color: MediFuelColors.navy),
            title: Text(photo['kind'] == 'RECEIPT' ? 'Fuel receipt' : 'Odometer photo'),
            subtitle: Text(photo['filename'] ?? ''),
          ),
        if (_error != null) Padding(padding: const EdgeInsets.only(top: 10), child: Text(_error!, style: const TextStyle(color: MediFuelColors.red))),
      ],
    );
  }

  Widget _footer() => SafeArea(
        top: false,
        child: Container(
          padding: const EdgeInsets.fromLTRB(18, 12, 18, 14),
          decoration: const BoxDecoration(color: Colors.white, border: Border(top: BorderSide(color: MediFuelColors.line))),
          child: Row(
            children: [
              if (_step > 0) ...[
                IconButton(tooltip: 'Previous step', onPressed: _back, icon: const Icon(Icons.arrow_back)),
                const SizedBox(width: 8),
              ],
              Expanded(
                child: FilledButton(
                  onPressed: _submitting ? null : (_step == 3 ? _submit : _next),
                  style: FilledButton.styleFrom(
                    backgroundColor: MediFuelColors.orange,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 15),
                  ),
                  child: _submitting
                      ? const SizedBox.square(dimension: 20, child: CircularProgressIndicator(strokeWidth: 2))
                      : Text(_step == 2 ? 'Next: review' : _step == 3 ? 'Submit entry' : 'Next'),
                ),
              ),
            ],
          ),
        ),
      );

  String? _positiveNumber(String? value, String message) {
    final number = double.tryParse((value ?? '').trim());
    return number == null || number <= 0 ? message : null;
  }
}

class _StepHeader extends StatelessWidget implements PreferredSizeWidget {
  const _StepHeader({required this.step});

  final int step;
  static const labels = ['Vehicle', 'Details', 'Photos', 'Review'];

  @override
  Size get preferredSize => const Size.fromHeight(46);

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Step ${step + 1} of 4 · ${labels[step]}', style: const TextStyle(color: Colors.white70, fontSize: 12)),
            const SizedBox(height: 9),
            Row(
              children: [
                for (var index = 0; index < 4; index++) ...[
                  Expanded(child: Container(height: 4, decoration: BoxDecoration(color: index <= step ? MediFuelColors.orange : Colors.white24, borderRadius: BorderRadius.circular(5)))),
                  if (index < 3) const SizedBox(width: 7),
                ],
              ],
            ),
          ],
        ),
      );
}

class _VehicleChoice extends StatelessWidget {
  const _VehicleChoice({required this.vehicle, required this.selected, required this.onTap});

  final FleetVehicle vehicle;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Card(
        color: selected ? const Color(0xFFFFF6F0) : Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(15),
          side: BorderSide(color: selected ? MediFuelColors.orange : MediFuelColors.line, width: selected ? 1.5 : 1),
        ),
        child: ListTile(
          onTap: onTap,
          leading: const CircleAvatar(backgroundColor: Color(0xFFEAF0F8), child: Icon(Icons.local_shipping_outlined, color: MediFuelColors.navy)),
          title: Text(vehicle.registration, style: const TextStyle(fontWeight: FontWeight.w800)),
          subtitle: Text(vehicle.title.isEmpty ? vehicle.fuelType : vehicle.title),
          trailing: Icon(selected ? Icons.check_circle : Icons.radio_button_unchecked, color: selected ? MediFuelColors.orange : MediFuelColors.muted),
        ),
      );
}

class _VehicleSummary extends StatelessWidget {
  const _VehicleSummary({required this.vehicle});

  final FleetVehicle? vehicle;

  @override
  Widget build(BuildContext context) => Card(
        child: ListTile(
          leading: const CircleAvatar(backgroundColor: Color(0xFFEAF0F8), child: Icon(Icons.local_shipping_outlined, color: MediFuelColors.navy)),
          title: Text(vehicle?.registration ?? '', style: const TextStyle(fontWeight: FontWeight.w800)),
          subtitle: Text(vehicle?.title ?? ''),
        ),
      );
}

class _TotalPreview extends StatelessWidget {
  const _TotalPreview({required this.total, required this.currency});

  final double total;
  final String currency;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: MediFuelColors.navy, borderRadius: BorderRadius.circular(15)),
        child: Row(
          children: [
            const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('Total cost · estimate', style: TextStyle(color: Colors.white70, fontSize: 12)), SizedBox(height: 4), Text('Final amount is calculated by the server', style: TextStyle(color: Colors.white70, fontSize: 10))])),
            Text('$currency ${NumberFormat('#,##0.00').format(total)}', style: const TextStyle(color: Colors.white, fontSize: 19, fontWeight: FontWeight.w800)),
          ],
        ),
      );
}

class _PhotoCard extends StatelessWidget {
  const _PhotoCard({required this.label, required this.photo, required this.onTap});

  final String label;
  final Map<String, String>? photo;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Card(
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Container(
                  width: 64,
                  height: 64,
                  decoration: BoxDecoration(color: const Color(0xFFEAF0F8), borderRadius: BorderRadius.circular(12)),
                  clipBehavior: Clip.antiAlias,
                  child: photo == null
                      ? const Icon(Icons.add_a_photo_outlined, color: MediFuelColors.navy)
                      : Image.memory(base64Decode(photo!['bytes']!), fit: BoxFit.cover),
                ),
                const SizedBox(width: 13),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(label, style: const TextStyle(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 4),
                    Text(photo == null ? 'Optional · camera or gallery' : 'Captured · tap to replace', style: const TextStyle(color: MediFuelColors.muted, fontSize: 11)),
                  ]),
                ),
                const Icon(Icons.chevron_right, color: MediFuelColors.muted),
              ],
            ),
          ),
        ),
      );
}

class _ReviewLine extends StatelessWidget {
  const _ReviewLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Row(
          children: [
            Expanded(child: Text(label, style: const TextStyle(color: MediFuelColors.muted, fontSize: 12))),
            Flexible(child: Text(value, textAlign: TextAlign.end, style: const TextStyle(color: MediFuelColors.ink, fontSize: 12, fontWeight: FontWeight.w700))),
          ],
        ),
      );
}

class _StepEmpty extends StatelessWidget {
  const _StepEmpty({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) => Card(child: Padding(padding: const EdgeInsets.all(18), child: Text(text, textAlign: TextAlign.center)));
}

String _fuelLabel(String value) => switch (value) {
      'DIESEL' => 'Diesel',
      'PETROL' => 'Petrol',
      'GASOLINE' => 'Gasoline',
      'ELECTRIC' => 'Electric',
      _ => 'Other',
    };