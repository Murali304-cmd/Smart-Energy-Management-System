import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/localization.dart';
import '../core/theme.dart';
import '../providers/user_profile_provider.dart';
import '../providers/energy_provider.dart';

class BatteryScreen extends StatelessWidget {
  const BatteryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<UserProfileProvider>();
    final energy = context.watch<EnergyProvider>();
    final isElder = profile.isElder;
    final lang = profile.language;
    final d = energy.dashboard;

    final isBackupSecured = d.backupHours >= 10.0;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 12.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Main SOC Status Card
          Container(
            padding: EdgeInsets.all(isElder ? 24 : 20),
            decoration: BoxDecoration(
              color: isElder ? Colors.white : const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(22),
              border: Border.all(
                color: isElder ? const Color(0xFF64748B) : Colors.white12,
                width: isElder ? 2.0 : 1.0,
              ),
            ),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      AppStrings.get('battery_stored', lang),
                      style: TextStyle(
                        fontSize: isElder ? 20 : 16,
                        fontWeight: FontWeight.w900,
                        color: isElder ? Colors.black : Colors.white,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppTheme.batteryGreen.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppTheme.batteryGreen, width: 1),
                      ),
                      child: Text(
                        d.batteryMode.toUpperCase(),
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          color: AppTheme.batteryGreen,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                // Circular SOC Display
                Stack(
                  alignment: Alignment.center,
                  children: [
                    SizedBox(
                      width: isElder ? 160 : 140,
                      height: isElder ? 160 : 140,
                      child: CircularProgressIndicator(
                        value: (d.batterySoc / 100.0).clamp(0.0, 1.0),
                        strokeWidth: isElder ? 16 : 12,
                        backgroundColor: Colors.grey.withOpacity(0.2),
                        valueColor: AlwaysStoppedAnimation<Color>(
                          d.batterySoc > 30 ? AppTheme.batteryGreen : Colors.redAccent,
                        ),
                      ),
                    ),
                    Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '${d.batterySoc.toStringAsFixed(0)}%',
                          style: TextStyle(
                            fontSize: isElder ? 38 : 32,
                            fontWeight: FontWeight.w900,
                            color: isElder ? Colors.black : Colors.white,
                          ),
                        ),
                        Text(
                          'State of Charge',
                          style: TextStyle(
                            fontSize: isElder ? 14 : 11,
                            color: isElder ? const Color(0xFF475569) : Colors.grey,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                // Backup Duration
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: isBackupSecured
                        ? Colors.green.withOpacity(0.12)
                        : Colors.amber.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: isBackupSecured ? Colors.green : Colors.amber,
                      width: 1.5,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        isBackupSecured ? Icons.check_circle_rounded : Icons.warning_amber_rounded,
                        color: isBackupSecured ? Colors.green : Colors.amber,
                        size: isElder ? 30 : 24,
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              isElder
                                  ? AppStrings.get('hours_backup_elder', lang)
                                  : '10-Hour Backup Target',
                              style: TextStyle(
                                fontSize: isElder ? 16 : 13,
                                fontWeight: FontWeight.w800,
                                color: isElder ? Colors.black : Colors.white,
                              ),
                            ),
                            Text(
                              '${d.backupHours.toStringAsFixed(1)} Hours Estimated @ Current Load',
                              style: TextStyle(
                                fontSize: isElder ? 15 : 12,
                                color: isBackupSecured ? Colors.green : Colors.amber,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Battery Physical Specifications
          Container(
            padding: EdgeInsets.all(isElder ? 18 : 14),
            decoration: BoxDecoration(
              color: isElder ? Colors.white : Theme.of(context).cardTheme.color,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                color: isElder ? const Color(0xFF94A3B8) : Colors.white10,
                width: isElder ? 1.5 : 1.0,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Physical BESS Telemetry',
                  style: TextStyle(
                    fontSize: isElder ? 17 : 14,
                    fontWeight: FontWeight.w800,
                    color: isElder ? Colors.black : null,
                  ),
                ),
                const SizedBox(height: 10),
                _buildInfoTile('Nominal Capacity', '20.0 kWh (Tesla Powerwall 2 / BESS)', isElder),
                _buildInfoTile('Current Battery Power', '${d.batteryPowerKw.toStringAsFixed(2)} kW', isElder),
                _buildInfoTile('Safe Minimum SOC', '20.0 % Reserve Limit', isElder),
                _buildInfoTile('Maximum Power Output', '10.0 kW Discharging Limit', isElder),
                _buildInfoTile('Health Index (SOH)', '98.4% (Optimal Cell Condition)', isElder),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // Multi-Zone Thermal BMS (Enterprise Feature 3)
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: isElder ? Colors.white : const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: isElder ? const Color(0xFF64748B) : Colors.white12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '🌡️ Multi-Zone Thermal BMS',
                      style: TextStyle(
                        fontSize: isElder ? 18 : 15,
                        fontWeight: FontWeight.w800,
                        color: isElder ? Colors.black : Colors.white,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: Colors.green.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Text('OPTIMAL', style: TextStyle(color: Colors.green, fontSize: 11, fontWeight: FontWeight.bold)),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(child: _buildZoneCard('Zone A (Anode)', '31.8 °C', isElder)),
                    const SizedBox(width: 8),
                    Expanded(child: _buildZoneCard('Zone B (Center)', '33.4 °C', isElder)),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(child: _buildZoneCard('Zone C (Cathode)', '32.1 °C', isElder)),
                    const SizedBox(width: 8),
                    Expanded(child: _buildZoneCard('Zone D (Terminals)', '34.0 °C', isElder)),
                  ],
                ),
                const SizedBox(height: 8),
                _buildInfoTile('Cooling Fan Relay', 'ACTIVE (Auto Controlled)', isElder),
                _buildInfoTile('Ambient Delta-T', '+4.5 °C (Safe Margin)', isElder),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // V2G & V2H Bidirectional Dispatch Hub (Enterprise Feature 2)
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: isElder ? Colors.white : const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: isElder ? const Color(0xFF64748B) : Colors.white12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '🚗 Bidirectional V2G / V2H Hub',
                      style: TextStyle(
                        fontSize: isElder ? 18 : 15,
                        fontWeight: FontWeight.w800,
                        color: isElder ? Colors.black : Colors.white,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: Colors.blue.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Text('CONNECTED', style: TextStyle(color: Colors.blue, fontSize: 11, fontWeight: FontWeight.bold)),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                _buildInfoTile('Electric Vehicle Model', 'Tata Nexon EV (60 kWh)', isElder),
                _buildInfoTile('Current EV Battery SOC', '72.0 % (19.2 kWh Dispatchable)', isElder),
                _buildInfoTile('Departure Schedule', '08:30 AM (Target: 85%)', isElder),
                _buildInfoTile('Min Emergency Reserve', '40.0 % Floor Limit', isElder),
                _buildInfoTile('V2H Peak-Shaving Savings', '₹ 48.50 / day', isElder),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildZoneCard(String name, String temp, bool isElder) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(name, style: TextStyle(fontSize: isElder ? 12 : 10, color: Colors.grey)),
          const SizedBox(height: 2),
          Text(temp, style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.green, fontSize: 13)),
        ],
      ),
    );
  }

  Widget _buildInfoTile(String label, String value, bool isElder) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: isElder ? 15 : 12,
              color: isElder ? const Color(0xFF334155) : Colors.grey,
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: isElder ? 15 : 12,
              fontWeight: FontWeight.bold,
              color: isElder ? Colors.black : null,
            ),
          ),
        ],
      ),
    );
  }
}
