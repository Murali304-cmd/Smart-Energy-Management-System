import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/localization.dart';
import '../providers/user_profile_provider.dart';
import '../providers/energy_provider.dart';
import '../services/tts_service.dart';

class CostBanner extends StatelessWidget {
  const CostBanner({super.key});

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<UserProfileProvider>();
    final energy = context.watch<EnergyProvider>();
    final isElder = profile.isElder;
    final lang = profile.language;
    final usage = energy.usage;
    final dashboard = energy.dashboard;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      padding: EdgeInsets.all(isElder ? 20 : 16),
      decoration: BoxDecoration(
        gradient: isElder
            ? const LinearGradient(
                colors: [Color(0xFFE2E8F0), Color(0xFFF1F5F9)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              )
            : const LinearGradient(
                colors: [Color(0xFF0369A1), Color(0xFF0284C7)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
        borderRadius: BorderRadius.circular(isElder ? 22 : 18),
        border: isElder
            ? Border.all(color: const Color(0xFF475569), width: 2.0)
            : null,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isElder ? 0.08 : 0.2),
            blurRadius: 10,
            offset: const Offset(0, 4),
          )
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: isElder ? Colors.black87 : Colors.white.withOpacity(0.2),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      Icons.electric_bolt_rounded,
                      color: isElder ? Colors.amberAccent : Colors.white,
                      size: isElder ? 26 : 20,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    isElder
                        ? AppStrings.get('today_cost_elder', lang)
                        : AppStrings.get('today_cost', lang),
                    style: TextStyle(
                      fontSize: isElder ? 18 : 14,
                      fontWeight: isElder ? FontWeight.w900 : FontWeight.w600,
                      color: isElder ? Colors.black : Colors.white.withOpacity(0.9),
                    ),
                  ),
                ],
              ),
              // Audio Speak Button for Elderly
              IconButton(
                icon: Icon(
                  TtsService().isPlaying ? Icons.volume_up_rounded : Icons.volume_up_outlined,
                  color: isElder ? const Color(0xFF0369A1) : Colors.white,
                  size: isElder ? 34 : 26,
                ),
                tooltip: AppStrings.get('speak_voice', lang),
                onPressed: () {
                  TtsService().speakSummary(
                    totalUnits: usage.totalUnitsToday,
                    cost: usage.totalAmountToday,
                    solarUnits: usage.solarUnitsToday,
                    backupHours: dashboard.backupHours,
                    language: lang,
                  );
                },
              ),
            ],
          ),
          const SizedBox(height: 12),
          // Total Amount for 1 Day
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                '₹ ${usage.totalAmountToday.toStringAsFixed(2)}',
                style: TextStyle(
                  fontSize: isElder ? 38 : 32,
                  fontWeight: FontWeight.w900,
                  color: isElder ? Colors.black : Colors.white,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '/ 1 Day',
                style: TextStyle(
                  fontSize: isElder ? 18 : 14,
                  fontWeight: FontWeight.w600,
                  color: isElder ? const Color(0xFF334155) : Colors.white.withOpacity(0.8),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Divider(height: 1, color: Colors.white24),
          const SizedBox(height: 12),
          // Units Used Breakdown Row
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isElder
                        ? AppStrings.get('today_units_elder', lang)
                        : AppStrings.get('today_units', lang),
                    style: TextStyle(
                      fontSize: isElder ? 15 : 12,
                      fontWeight: isElder ? FontWeight.w800 : FontWeight.w500,
                      color: isElder ? const Color(0xFF1E293B) : Colors.white.withOpacity(0.85),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${usage.totalUnitsToday.toStringAsFixed(2)} Units',
                    style: TextStyle(
                      fontSize: isElder ? 22 : 18,
                      fontWeight: FontWeight.w900,
                      color: isElder ? Colors.black : Colors.white,
                    ),
                  ),
                ],
              ),
              // Solar Savings
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    isElder
                        ? AppStrings.get('solar_savings_elder', lang)
                        : AppStrings.get('solar_savings', lang),
                    style: TextStyle(
                      fontSize: isElder ? 15 : 12,
                      fontWeight: isElder ? FontWeight.w800 : FontWeight.w500,
                      color: isElder ? const Color(0xFF047857) : Colors.greenAccent,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '₹ ${usage.moneySavedToday.toStringAsFixed(2)} Saved',
                    style: TextStyle(
                      fontSize: isElder ? 22 : 18,
                      fontWeight: FontWeight.w900,
                      color: isElder ? const Color(0xFF065F46) : Colors.white,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.wb_sunny_rounded, size: 14, color: Colors.amberAccent),
                    const SizedBox(width: 4),
                    Text(
                      'CEI: ${usage.cleanEnergyIndexPct.toStringAsFixed(0)}% Clean',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: isElder ? Colors.black87 : Colors.white),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.battery_charging_full_rounded, size: 14, color: Colors.greenAccent),
                    const SizedBox(width: 4),
                    Text(
                      'Backup: ${dashboard.backupHours.toStringAsFixed(1)} hrs',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: isElder ? Colors.black87 : Colors.white),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
