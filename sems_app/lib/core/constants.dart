class AppConstants {
  // Backend API URL (configured to this computer's local Wi-Fi IP)
  static const String defaultBaseUrl = 'http://10.33.45.111:8080';
  static const String localBaseUrl = 'http://127.0.0.1:8080';

  // API Endpoints
  static const String endpointDashboard = '/api/dashboard';
  static const String endpointBattery = '/api/battery';
  static const String endpointBatteryBackup = '/api/battery/backup';
  static const String endpointEnergyManagement = '/api/energy-management';
  static const String endpointHealth = '/api/health';
  static const String endpointAlerts = '/api/alerts';

  // Battery System Specifications
  static const double batteryCapacityKWh = 20.0;
  static const double batteryMinSoc = 20.0;
  static const double batteryMaxSoc = 100.0;
  static const double solarCapacityKW = 4.0;

  // Notification Channels
  static const String hourlyNotificationChannelId = 'sems_hourly_reports';
  static const String hourlyNotificationChannelName = 'Hourly Energy Reports';
  static const String hourlyNotificationChannelDesc = 'Delivers hourly updates on units consumed and estimated cost.';

  static const String alertNotificationChannelId = 'sems_critical_alerts';
  static const String alertNotificationChannelName = 'Energy Safety & Grid Alerts';
  static const String alertNotificationChannelDesc = 'Alerts for battery health, high usage, or grid outages.';

  // Current Official TANGEDCO / TNEB Domestic Tariff Structure (LT-IA)
  // Slab 1: 0 - 100 units -> FREE (0 INR Government Subsidy)
  // Slab 2: 101 - 400 units -> Rs 4.70 / unit
  // Slab 3: 401 - 500 units -> Rs 6.30 / unit
  // Slab 4: 501 - 600 units -> Rs 8.40 / unit
  // Slab 5: 601 - 800 units -> Rs 9.45 / unit
  // Slab 6: 801 - 1000 units -> Rs 10.50 / unit
  // Slab 7: 1000+ units -> Rs 11.55 / unit
  static const double defaultGridTariffRate = 4.70; // INR per unit for standard estimate
}
