import 'dart:async';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'constants.dart';
import 'localization.dart';

class NotificationService {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final FlutterLocalNotificationsPlugin _notifications = FlutterLocalNotificationsPlugin();
  bool _isInitialized = false;
  Timer? _hourlyTimer;

  Future<void> initialize() async {
    if (_isInitialized) return;

    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    const initSettings = InitializationSettings(android: androidSettings, iOS: iosSettings);

    try {
      await _notifications.initialize(
        initSettings,
        onDidReceiveNotificationResponse: (details) {
          // Handle notification tap
        },
      );

      // Create Android Notification Channels
      const androidChannel = AndroidNotificationChannel(
        AppConstants.hourlyNotificationChannelId,
        AppConstants.hourlyNotificationChannelName,
        description: AppConstants.hourlyNotificationChannelDesc,
        importance: Importance.high,
        playSound: true,
      );

      final androidPlugin = _notifications.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
      if (androidPlugin != null) {
        await androidPlugin.createNotificationChannel(androidChannel);
        await androidPlugin.requestNotificationsPermission();
      }

      _isInitialized = true;
    } catch (e) {
      // Fallback in case of emulator or permission issues
      _isInitialized = true;
    }
  }

  /// Start hourly periodic local notification timer (fires every 60 minutes)
  void startHourlyNotifications({
    required double Function() getCurrentHourUnits,
    required double Function() getTotalDayUnits,
    required double Function() getTodayCost,
    required AppLanguage Function() getLanguage,
  }) {
    _hourlyTimer?.cancel();
    // Schedule repeating timer every hour (for demo testing, also fires initially after 30s)
    _hourlyTimer = Timer.periodic(const Duration(hours: 1), (timer) {
      final hourUnits = getCurrentHourUnits();
      final totalUnits = getTotalDayUnits();
      final cost = getTodayCost();
      final lang = getLanguage();

      sendHourlyReport(
        hourUnits: hourUnits,
        totalUnits: totalUnits,
        cost: cost,
        language: lang,
      );
    });
  }

  void stopHourlyNotifications() {
    _hourlyTimer?.cancel();
  }

  /// Fire an immediate hourly report notification
  Future<void> sendHourlyReport({
    required double hourUnits,
    required double totalUnits,
    required double cost,
    required AppLanguage language,
  }) async {
    final title = AppStrings.get('notification_hourly_title', language);
    final bodyTemplate = AppStrings.get('notification_hourly_body', language);

    final body = bodyTemplate
        .replaceAll('{hour_units}', hourUnits.toStringAsFixed(2))
        .replaceAll('{total_units}', totalUnits.toStringAsFixed(2))
        .replaceAll('{cost}', cost.toStringAsFixed(2));

    const androidDetails = AndroidNotificationDetails(
      AppConstants.hourlyNotificationChannelId,
      AppConstants.hourlyNotificationChannelName,
      channelDescription: AppConstants.hourlyNotificationChannelDesc,
      importance: Importance.high,
      priority: Priority.high,
      icon: '@mipmap/ic_launcher',
    );

    const iosDetails = DarwinNotificationDetails();
    const details = NotificationDetails(android: androidDetails, iOS: iosDetails);

    try {
      await _notifications.show(
        DateTime.now().hour, // notification id based on hour
        title,
        body,
        details,
      );
    } catch (_) {}
  }

  /// Critical Battery or Grid Alert Notification
  Future<void> sendCriticalAlert({
    required String title,
    required String message,
  }) async {
    const androidDetails = AndroidNotificationDetails(
      AppConstants.alertNotificationChannelId,
      AppConstants.alertNotificationChannelName,
      importance: Importance.max,
      priority: Priority.max,
    );
    const details = NotificationDetails(android: androidDetails, iOS: DarwinNotificationDetails());

    try {
      await _notifications.show(999, title, message, details);
    } catch (_) {}
  }
}
