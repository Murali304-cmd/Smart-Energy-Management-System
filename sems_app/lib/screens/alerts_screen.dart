import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/localization.dart';
import '../core/notification_service.dart';
import '../providers/user_profile_provider.dart';
import '../providers/energy_provider.dart';
import '../models/alert_model.dart';

class AlertsScreen extends StatelessWidget {
  const AlertsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<UserProfileProvider>();
    final energy = context.watch<EnergyProvider>();
    final isElder = profile.isElder;
    final lang = profile.language;
    final alerts = energy.alerts;
    final usage = energy.usage;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          AppStrings.get('tab_alerts', lang),
          style: TextStyle(
            fontSize: isElder ? 22 : 18,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Test Hourly Notification Card
            Container(
              padding: EdgeInsets.all(isElder ? 18 : 14),
              decoration: BoxDecoration(
                color: const Color(0xFF0284C7).withOpacity(0.12),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFF0284C7), width: 1.5),
              ),
              child: Row(
                children: [
                  const Icon(Icons.notifications_active_rounded, color: Color(0xFF0284C7), size: 30),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          isElder ? 'மணிநேர அறிவிப்பை பரிசோதிக்கவும்' : 'Test Hourly Notification',
                          style: TextStyle(
                            fontSize: isElder ? 16 : 14,
                            fontWeight: FontWeight.bold,
                            color: isElder ? Colors.black : Colors.white,
                          ),
                        ),
                        Text(
                          isElder
                              ? 'இப்போதே உங்கள் மொபைலில் அறிவிப்பு எப்படி தோன்றும் என்பதை பார்க்கலாம்.'
                              : 'Trigger an immediate test push notification for current hour units & cost.',
                          style: TextStyle(
                            fontSize: isElder ? 14 : 11,
                            color: isElder ? const Color(0xFF334155) : Colors.grey,
                          ),
                        ),
                      ],
                    ),
                  ),
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF0284C7),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    onPressed: () {
                      NotificationService().sendHourlyReport(
                        hourUnits: usage.currentHourUnits,
                        totalUnits: usage.totalUnitsToday,
                        cost: usage.totalAmountToday,
                        language: lang,
                      );
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Hourly notification dispatched!')),
                      );
                    },
                    child: const Text('Test'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            Text(
              isElder ? 'அறிவிப்பு வரலாறு' : 'Hourly Reports & System Alerts',
              style: TextStyle(
                fontSize: isElder ? 18 : 15,
                fontWeight: FontWeight.w800,
                color: isElder ? Colors.black : null,
              ),
            ),
            const SizedBox(height: 10),

            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: alerts.length,
              itemBuilder: (context, index) {
                final item = alerts[index];
                return Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: EdgeInsets.all(isElder ? 16 : 12),
                  decoration: BoxDecoration(
                    color: isElder ? Colors.white : Theme.of(context).cardTheme.color,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: isElder ? const Color(0xFF94A3B8) : Colors.white10,
                      width: isElder ? 1.5 : 1.0,
                    ),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: _getSeverityColor(item.severity).withOpacity(0.15),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          _getTypeIcon(item.type),
                          color: _getSeverityColor(item.severity),
                          size: isElder ? 26 : 20,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              item.title,
                              style: TextStyle(
                                fontSize: isElder ? 16 : 13,
                                fontWeight: FontWeight.bold,
                                color: isElder ? Colors.black : null,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              item.message,
                              style: TextStyle(
                                fontSize: isElder ? 14 : 12,
                                color: isElder ? const Color(0xFF334155) : Colors.grey,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Color _getSeverityColor(AlertSeverity sev) {
    switch (sev) {
      case AlertSeverity.critical:
        return Colors.redAccent;
      case AlertSeverity.warning:
        return Colors.amber;
      case AlertSeverity.info:
        return const Color(0xFF0284C7);
    }
  }

  IconData _getTypeIcon(String type) {
    switch (type) {
      case 'hourly':
        return Icons.access_time_rounded;
      case 'solar':
        return Icons.wb_sunny_rounded;
      case 'battery':
        return Icons.battery_charging_full_rounded;
      default:
        return Icons.notifications_rounded;
    }
  }
}
