import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite/sqflite.dart';

import 'models.dart';

class LocalStore {
  static const _queueKey = 'medifuel.pending.entries.v1';
  static const _vehiclesKey = 'medifuel.cached.vehicles.v1';
  static const _purchasesKey = 'medifuel.cached.purchases.v1';

  SharedPreferencesAsync? _preferencesInstance;
  Database? _database;

  SharedPreferencesAsync get _preferences => _preferencesInstance ??= SharedPreferencesAsync();

  Future<void> initialize() async {
    if (kIsWeb) return;
    final directory = await getApplicationDocumentsDirectory();
    _database = await openDatabase(
      path.join(directory.path, 'medifuel_offline.db'),
      version: 1,
      onCreate: (database, version) async {
        await database.execute('''
          CREATE TABLE pending_entries (
            local_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL
          )
        ''');
      },
    );
  }

  Future<void> enqueue(PendingFuelEntry entry) async {
    if (kIsWeb) {
      final entries = await _readWebQueue();
      entries.removeWhere((item) => item.localId == entry.localId);
      entries.add(entry);
      await _writeWebQueue(entries);
      return;
    }
    await _database!.insert(
      'pending_entries',
      {
        'local_id': entry.localId,
        'payload': entry.encode(),
        'created_at': DateTime.now().toUtc().toIso8601String(),
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<List<PendingFuelEntry>> pendingEntries() async {
    if (kIsWeb) return _readWebQueue();
    final rows = await _database!.query('pending_entries', orderBy: 'created_at ASC');
    return rows
        .map((row) => PendingFuelEntry.fromJson(jsonDecode(row['payload'] as String) as Map<String, dynamic>))
        .toList();
  }

  Future<void> removePending(String localId) async {
    if (kIsWeb) {
      final entries = await _readWebQueue()..removeWhere((item) => item.localId == localId);
      await _writeWebQueue(entries);
      return;
    }
    await _database!.delete('pending_entries', where: 'local_id = ?', whereArgs: [localId]);
  }

  Future<void> updatePending(PendingFuelEntry entry) => enqueue(entry);

  Future<List<FleetVehicle>> cachedVehicles() async {
    final raw = await _preferences.getString(_vehiclesKey);
    if (raw == null) return const [];
    return (jsonDecode(raw) as List<dynamic>)
        .map((item) => FleetVehicle.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
  }

  Future<void> cacheVehicles(List<Map<String, dynamic>> json) =>
      _preferences.setString(_vehiclesKey, jsonEncode(json));

  Future<List<FuelPurchase>> cachedPurchases() async {
    final raw = await _preferences.getString(_purchasesKey);
    if (raw == null) return const [];
    return (jsonDecode(raw) as List<dynamic>)
        .map((item) => FuelPurchase.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
  }

  Future<void> cachePurchases(List<Map<String, dynamic>> json) =>
      _preferences.setString(_purchasesKey, jsonEncode(json));

  Future<List<PendingFuelEntry>> _readWebQueue() async {
    final raw = await _preferences.getString(_queueKey);
    if (raw == null) return [];
    return (jsonDecode(raw) as List<dynamic>)
        .map((item) => PendingFuelEntry.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
  }

  Future<void> _writeWebQueue(List<PendingFuelEntry> entries) =>
      _preferences.setString(_queueKey, jsonEncode(entries.map((entry) => entry.toJson()).toList()));

  Future<void> close() async => _database?.close();
}