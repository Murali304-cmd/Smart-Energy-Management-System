import 'dart:async';
import 'package:flutter/material.dart';
import '../core/notification_service.dart';
import '../models/dashboard_model.dart';
import '../models/energy_usage_model.dart';
import '../models/alert_model.dart';
import '../services/api_service.dart';
import '../services/usage_calculator.dart';
import 'user_profile_provider.dart';

class EnergyProvider extends ChangeNotifier {
  final ApiService _apiService = ApiService();
  final NotificationService _notificationService = NotificationService();

  DashboardModel _dashboard = DashboardModel.mock();
  EnergyUsageModel _usage = EnergyUsageModel.createMock();
  List<AlertItem> _alerts = AlertItem.getSampleAlerts();
  List<ApplianceUsageItem> _appliances = UsageCalculator.getDefaultAppliances();

  bool _isLoading = false;
  Timer? _pollingTimer;

  DashboardModel get dashboard => _dashboard;
  EnergyUsageModel get usage => _usage;
  List<AlertItem> get alerts => _alerts;
  List<ApplianceUsageItem> get appliances => _appliances;
  bool get isLoading => _isLoading;
  String get serverBaseUrl => _apiService.baseUrl;
  ApiService get apiService => _apiService;

  EnergyProvider() {
    refreshData();
    // Periodic refresh every 30 seconds
    _pollingTimer = Timer.periodic(const Duration(seconds: 30), (_) => refreshData());
  }

  void setBaseUrl(String url) {
    _apiService.baseUrl = url;
    refreshData();
  }

  /// Initialize hourly notifications hooked with UserProfileProvider
  void setupHourlyNotifications(UserProfileProvider profile) {
    if (profile.hourlyNotificationsEnabled) {
      _notificationService.startHourlyNotifications(
        getCurrentHourUnits: () => _usage.currentHourUnits,
        getTotalDayUnits: () => _usage.totalUnitsToday,
        getTodayCost: () => _usage.totalAmountToday,
        getLanguage: () => profile.language,
      );
    } else {
      _notificationService.stopHourlyNotifications();
    }
  }

  Future<void> refreshData() async {
    _isLoading = true;
    notifyListeners();

    try {
      final fetched = await _apiService.fetchDashboard();
      _dashboard = fetched;

      // Update unit consumption model
      _usage = EnergyUsageModel.createMock(
        currentLoadKw: _dashboard.loadKw,
        solarKw: _dashboard.solarKw,
      );
    } catch (_) {
      // Fallback
      _dashboard = DashboardModel.mock();
      _usage = EnergyUsageModel.createMock();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void updateApplianceHours(String id, double hours) {
    final index = _appliances.indexWhere((item) => item.id == id);
    if (index != -1) {
      _appliances[index].hoursUsed = hours;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    super.dispose();
  }
}
