import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/localization.dart';
import '../providers/user_profile_provider.dart';
import '../providers/energy_provider.dart';
import '../services/usage_calculator.dart';

class ApplianceScreen extends StatelessWidget {
  const ApplianceScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<UserProfileProvider>();
    final energy = context.watch<EnergyProvider>();
    final isElder = profile.isElder;
    final lang = profile.language;
    final appliances = energy.appliances;

    final totalUnits = UsageCalculator.calculateTotalApplianceUnits(appliances);
    final totalCost = UsageCalculator.calculateTotalApplianceCost(appliances);

    return Scaffold(
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header Summary Card
            Container(
              padding: EdgeInsets.all(isElder ? 20 : 16),
              decoration: BoxDecoration(
                color: isElder ? Colors.white : const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(
                  color: isElder ? const Color(0xFF64748B) : Colors.white12,
                  width: isElder ? 2.0 : 1.0,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isElder ? 'வீட்டு உபகரணங்கள் வாரியான பயன்பாடு' : 'Appliance-Wise Consumption',
                    style: TextStyle(
                      fontSize: isElder ? 19 : 16,
                      fontWeight: FontWeight.w900,
                      color: isElder ? Colors.black : Colors.white,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    isElder
                        ? 'ஒவ்வொரு உபகரணமும் எத்தனை மணி நேரம் ஓடியது மற்றும் எத்தனை யூனிட் ஆனது என்பதை அறியலாம்.'
                        : 'Adjust runtime hours to estimate appliance unit usage and daily cost.',
                    style: TextStyle(
                      fontSize: isElder ? 15 : 12,
                      color: isElder ? const Color(0xFF334155) : Colors.grey,
                    ),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Estimated Appliance Units',
                            style: TextStyle(fontSize: isElder ? 14 : 11, color: Colors.grey),
                          ),
                          Text(
                            '${totalUnits.toStringAsFixed(2)} Units',
                            style: TextStyle(
                              fontSize: isElder ? 24 : 20,
                              fontWeight: FontWeight.w900,
                              color: const Color(0xFF0284C7),
                            ),
                          ),
                        ],
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(
                            'Estimated Cost',
                            style: TextStyle(fontSize: isElder ? 14 : 11, color: Colors.grey),
                          ),
                          Text(
                            '₹ ${totalCost.toStringAsFixed(2)}',
                            style: TextStyle(
                              fontSize: isElder ? 24 : 20,
                              fontWeight: FontWeight.w900,
                              color: const Color(0xFF10B981),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Appliance List
            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: appliances.length,
              itemBuilder: (context, index) {
                final item = appliances[index];
                return Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: EdgeInsets.all(isElder ? 18 : 14),
                  decoration: BoxDecoration(
                    color: isElder ? Colors.white : Theme.of(context).cardTheme.color,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                      color: isElder ? const Color(0xFF94A3B8) : Colors.white10,
                      width: isElder ? 1.5 : 1.0,
                    ),
                  ),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          Text(item.icon, style: TextStyle(fontSize: isElder ? 32 : 24)),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  AppStrings.get(item.nameKey, lang),
                                  style: TextStyle(
                                    fontSize: isElder ? 17 : 14,
                                    fontWeight: FontWeight.w800,
                                    color: isElder ? Colors.black : null,
                                  ),
                                ),
                                Text(
                                  'Power: ${item.wattage.toInt()} W',
                                  style: TextStyle(
                                    fontSize: isElder ? 14 : 11,
                                    color: isElder ? const Color(0xFF475569) : Colors.grey,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Text(
                                '${item.unitsConsumed.toStringAsFixed(2)} Units',
                                style: TextStyle(
                                  fontSize: isElder ? 18 : 14,
                                  fontWeight: FontWeight.w900,
                                  color: const Color(0xFF0284C7),
                                ),
                              ),
                              Text(
                                '₹ ${item.estimatedCost.toStringAsFixed(2)}',
                                style: TextStyle(
                                  fontSize: isElder ? 15 : 12,
                                  fontWeight: FontWeight.bold,
                                  color: const Color(0xFF10B981),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      // Slider for runtime hours
                      Row(
                        children: [
                          Text(
                            '${item.hoursUsed.toStringAsFixed(1)}h',
                            style: TextStyle(
                              fontSize: isElder ? 16 : 13,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          Expanded(
                            child: Slider(
                              value: item.hoursUsed,
                              min: 0.0,
                              max: 24.0,
                              divisions: 48,
                              activeColor: const Color(0xFF0284C7),
                              onChanged: (val) {
                                energy.updateApplianceHours(item.id, val);
                              },
                            ),
                          ),
                          const Text('24h'),
                        ],
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
}
