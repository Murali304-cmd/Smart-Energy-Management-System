enum AlertSeverity { info, warning, critical }

class AlertItem {
  final String id;
  final String title;
  final String message;
  final DateTime timestamp;
  final AlertSeverity severity;
  final String type; // 'hourly', 'battery', 'solar', 'grid'

  AlertItem({
    required this.id,
    required this.title,
    required this.message,
    required this.timestamp,
    required this.severity,
    required this.type,
  });

  static List<AlertItem> getSampleAlerts() {
    final now = DateTime.now();
    return [
      AlertItem(
        id: '1',
        title: '⚡ Hourly Energy Summary (Current Hour)',
        message: 'Units used: 1.85 kWh | Today\'s Total: 14.20 Units | Estimated Cost: ₹28.50',
        timestamp: now.subtract(const Duration(minutes: 5)),
        severity: AlertSeverity.info,
        type: 'hourly',
      ),
      AlertItem(
        id: '2',
        title: '☀️ Solar Peak Efficiency Active',
        message: 'Solar irradiance peaked at 860 W/m². Home running 100% on solar power.',
        timestamp: now.subtract(const Duration(hours: 1)),
        severity: AlertSeverity.info,
        type: 'solar',
      ),
      AlertItem(
        id: '3',
        title: '🔋 Battery 10-Hour Backup Secured',
        message: 'Battery SOC at 82%. Estimated backup duration: 9.4 hours remaining.',
        timestamp: now.subtract(const Duration(hours: 2)),
        severity: AlertSeverity.info,
        type: 'battery',
      ),
      AlertItem(
        id: '4',
        title: '⚡ Hourly Energy Summary (Past Hour)',
        message: 'Units used: 2.10 kWh | TNEB Slab: Slab 2 (₹4.70/unit)',
        timestamp: now.subtract(const Duration(hours: 3)),
        severity: AlertSeverity.info,
        type: 'hourly',
      ),
    ];
  }
}
