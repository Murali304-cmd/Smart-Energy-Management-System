import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/localization.dart';

class UserProfileProvider extends ChangeNotifier {
  UserAgeMode _ageMode = UserAgeMode.young;
  AppLanguage _language = AppLanguage.english;
  bool _isDarkMode = false;
  bool _hourlyNotificationsEnabled = true;
  double _userBudget = 25.0;
  bool _hasCompletedOnboarding = false;

  UserAgeMode get ageMode => _ageMode;
  AppLanguage get language => _language;
  bool get isDarkMode => _isDarkMode;
  bool get hourlyNotificationsEnabled => _hourlyNotificationsEnabled;
  double get userBudget => _userBudget;
  bool get hasCompletedOnboarding => _hasCompletedOnboarding;
  bool get isElder => false;

  UserProfileProvider() {
    _loadPreferences();
  }

  Future<void> _loadPreferences() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _ageMode = UserAgeMode.young;

      final langIndex = prefs.getInt('app_language');
      if (langIndex != null && langIndex >= 0 && langIndex < AppLanguage.values.length) {
        _language = AppLanguage.values[langIndex];
      }

      _isDarkMode = prefs.getBool('is_dark_mode') ?? false;
      _hourlyNotificationsEnabled = prefs.getBool('hourly_notifications') ?? true;
      _userBudget = prefs.getDouble('user_budget') ?? 25.0;
      _hasCompletedOnboarding = prefs.getBool('has_completed_onboarding') ?? false;

      notifyListeners();
    } catch (_) {}
  }

  Future<void> setAgeMode(UserAgeMode mode) async {
    _ageMode = mode;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt('user_age_mode', mode.index);
  }

  Future<void> setLanguage(AppLanguage lang) async {
    _language = lang;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt('app_language', lang.index);
  }

  Future<void> setDarkMode(bool dark) async {
    _isDarkMode = dark;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('is_dark_mode', dark);
  }

  Future<void> setHourlyNotifications(bool enabled) async {
    _hourlyNotificationsEnabled = enabled;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('hourly_notifications', enabled);
  }

  Future<void> setBudget(double budget) async {
    _userBudget = budget;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble('user_budget', budget);
  }

  Future<void> completeOnboarding() async {
    _hasCompletedOnboarding = true;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('has_completed_onboarding', true);
  }
}
