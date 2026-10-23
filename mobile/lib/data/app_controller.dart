import 'dart:convert';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:uuid/uuid.dart';

import 'api_client.dart';
import 'local_store.dart';
import 'models.dart';

class AppController extends ChangeNotifier {
  AppController({required this.api, required this.store});

  final ApiClient api;
  final LocalStore store;
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();
  final Connectivity _connectivity = Connectivity();
  final Uuid _uuid = const Uuid();
  static const _savedUserKey = 'session_user';

  AppUser? user;
  FleetSummary summary = const FleetSummary();
  List<FleetVehicle> vehicles = const [];
  List<FuelPurchase> purchases = const [];
  List<Map<String, dynamic>> openAlerts = const [];
  List<PendingFuelEntry> pending = const [];
  String currency = 'USD';
  String? error;
  bool busy = false;
  bool online = true;
  bool initialized = false;

  Future<void> initialize() async {
    await store.initialize();
    pending = await store.pendingEntries();
    final storedToken = await _secureStorage.read(key: 'access_token');
    if (storedToken != null) {
      api.token = storedToken;
      try {
        user = AppUser.fromJson(await api.currentUser());
        await _secureStorage.write(key: _savedUserKey, value: jsonEncode(user!.toJson()));
        await _loadRemoteData();
      } on ApiException catch (exception) {
        if (exception.statusCode == 401) {
          await _clearSession();
        } else {
          await _restoreSavedUser();
          error = exception.message;
        }
        await _loadCachedData();
      } catch (_) {
        await _restoreSavedUser();
        await _loadCachedData();
      }
    }
    initialized = true;
    notifyListeners();
    _connectivity.onConnectivityChanged.listen((results) {
      online = results.any((result) => result != ConnectivityResult.none);
      notifyListeners();
      if (online && user != null) syncPending();
    });
    final current = await _connectivity.checkConnectivity();
    online = current.any((result) => result != ConnectivityResult.none);
    notifyListeners();
  }

  Future<void> login(String email, String password, {bool remember = true}) async {
    busy = true;
    error = null;
    notifyListeners();
    try {
      final result = await api.login(email, password);
      api.token = result['access_token'] as String;
      if (remember) {
        await _secureStorage.write(key: 'access_token', value: api.token);
      } else {
        await _secureStorage.delete(key: 'access_token');
      }
      user = AppUser.fromJson(await api.currentUser());
      if (remember) await _secureStorage.write(key: _savedUserKey, value: jsonEncode(user!.toJson()));
      await _loadRemoteData();
    } on ApiException catch (exception) {
      error = exception.message;
      rethrow;
    } catch (_) {
      error = 'Could not connect. Check your connection and try again.';
      rethrow;
    } finally {
      busy = false;
      notifyListeners();
    }
  }

  Future<String> register({
    required String invitationToken,
    required String fullName,
    required String password,
  }) async {
    busy = true;
    error = null;
    notifyListeners();
    try {
      final result = await api.register(
        invitationToken: invitationToken,
        fullName: fullName,
        password: password,
      );
      return result['email'] as String;
    } on ApiException catch (exception) {
      error = exception.message;
      rethrow;
    } finally {
      busy = false;
      notifyListeners();
    }
  }

  Future<void> requestPasswordReset(String email) => api.requestPasswordReset(email);

  Future<void> logout() async {
    try {
      if (api.token != null) await api.logout();
    } finally {
      await _clearSession();
      notifyListeners();
    }
  }

  Future<void> refresh() async {
    if (user == null) return;
    busy = true;
    error = null;
    notifyListeners();
    try {
      await _loadRemoteData();
    } on ApiException catch (exception) {
      error = exception.message;
      await _loadCachedData();
    } catch (_) {
      error = 'You are offline. Showing saved data.';
      await _loadCachedData();
    } finally {
      busy = false;
      notifyListeners();
    }
  }

  Future<bool> saveFuelEntry({
    required String vehicleId,
    required int odometer,
    required String fuelType,
    required String litres,
    required String pricePerLitre,
    required DateTime purchasedAt,
    required String? station,
    required List<Map<String, String>> attachments,
  }) async {
    if (user?.organizationId == null) {
      throw const ApiException('This account has no fleet organization.');
    }
    final entry = PendingFuelEntry(
      localId: _uuid.v4(),
      record: {
        'client_record_id': _uuid.v4(),
        'vehicle_id': vehicleId,
        'odometer_reading': odometer,
        'fuel_type': fuelType.toUpperCase(),
        'litres_purchased': litres,
        'price_per_litre': pricePerLitre,
        'currency': currency,
        'station_name': station?.trim().isEmpty == true ? null : station?.trim(),
        'purchased_at': purchasedAt.toUtc().toIso8601String(),
        'source': 'OFFLINE',
      },
      attachments: attachments,
    );
    await store.enqueue(entry);
    pending = await store.pendingEntries();
    notifyListeners();
    if (online) await syncPending();
    return pending.any((item) => item.localId == entry.localId);
  }

  Future<void> syncPending() async {
    if (user == null || api.token == null || pending.isEmpty || busy) return;
    busy = true;
    error = null;
    notifyListeners();
    try {
      final entries = await store.pendingEntries();
      for (var start = 0; start < entries.length; start += 50) {
        final batch = entries.skip(start).take(50).toList();
        final results = await api.syncFuelRecords(batch.map((entry) => entry.record).toList());
        for (var index = 0; index < batch.length && index < results.length; index++) {
          final entry = batch[index];
          final result = results[index];
          final status = result['status'];
          if (status != 'accepted' && status != 'already_accepted') {
            await store.updatePending(
              entry.withError(result['error']?.toString() ?? 'Could not sync yet.'),
            );
            continue;
          }
          final recordId = result['record_id']?.toString();
          try {
            if (recordId != null) {
              for (final attachment in entry.attachments) {
                await api.uploadAttachment(
                  recordId: recordId,
                  kind: attachment['kind']!,
                  filename: attachment['filename']!,
                  contentType: attachment['content_type']!,
                  bytes: base64Decode(attachment['bytes']!),
                );
              }
            }
            await store.removePending(entry.localId);
          } on ApiException catch (exception) {
            await store.updatePending(entry.withError(exception.message));
          }
        }
      }
      pending = await store.pendingEntries();
      await _loadRemoteData();
    } on ApiException catch (exception) {
      error = exception.message;
    } catch (_) {
      error = 'Sync paused. Your entries are still saved on this device.';
    } finally {
      busy = false;
      notifyListeners();
    }
  }

  Future<void> _loadRemoteData() async {
    final currentUser = user;
    final organizationId = currentUser?.organizationId;
    if (currentUser == null || organizationId == null) return;
    final results = await Future.wait<Object>([
      api.dashboard(),
      api.vehicles(),
      api.fuelRecords(),
      api.alerts(),
      api.organization(organizationId),
    ]);
    summary = FleetSummary.fromJson(results[0] as Map<String, dynamic>);
    final vehicleJson = results[1] as List<Map<String, dynamic>>;
    final purchaseJson = results[2] as List<Map<String, dynamic>>;
    purchases = purchaseJson.map(FuelPurchase.fromJson).toList();
    vehicles = vehicleJson.map((item) => FleetVehicle.fromJson(item).withHistory(purchases)).toList();
    openAlerts = results[3] as List<Map<String, dynamic>>;
    currency = (results[4] as Map<String, dynamic>)['default_currency'] as String? ?? 'USD';
    await store.cacheVehicles(vehicleJson);
    await store.cachePurchases(purchaseJson);
    pending = await store.pendingEntries();
  }

  Future<void> _loadCachedData() async {
    final vehicleRows = await store.cachedVehicles();
    purchases = await store.cachedPurchases();
    vehicles = vehicleRows.map((vehicle) => vehicle.withHistory(purchases)).toList();
    pending = await store.pendingEntries();
  }

  Future<void> _clearSession() async {
    api.token = null;
    user = null;
    await _secureStorage.delete(key: 'access_token');
    await _secureStorage.delete(key: _savedUserKey);
  }

  Future<void> _restoreSavedUser() async {
    final saved = await _secureStorage.read(key: _savedUserKey);
    if (saved != null) user = AppUser.fromJson(jsonDecode(saved) as Map<String, dynamic>);
  }
}