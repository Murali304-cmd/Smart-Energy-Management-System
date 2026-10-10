import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/localization.dart';
import '../providers/user_profile_provider.dart';
import '../providers/energy_provider.dart';
import '../models/energy_usage_model.dart';

class TnebCompareScreen extends StatelessWidget {
  const TnebCompareScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<UserProfileProvider>();
    final energy = context.watch<EnergyProvider>();
    final isElder = profile.isElder;
    final lang = profile.language;
    final usage = energy.usage;

    // Calculations
    final standardWithoutSolar = EnergyUsageModel.calculateTnebBill(usage.totalUnitsToday);
    final standardBill = standardWithoutSolar['amount'] as double;
    final semsBill = usage.totalAmountToday;
    final savedAmount = (standardBill - semsBill) > 0 ? (standardBill - semsBill) : (usage.solarUnitsToday * 4.70);
    final savingsPercent = standardBill > 0 ? ((savedAmount / standardBill) * 100).clamp(0.0, 100.0) : 75.0;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          AppStrings.get('compare_tneb', lang),
          style: TextStyle(
            fontSize: isElder ? 20 : 18,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Big Savings Highlight
            Container(
              padding: EdgeInsets.all(isElder ? 22 : 18),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF065F46), Color(0xFF059669)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.15),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  )
                ],
              ),
              child: Column(
                children: [
                  Text(
                    isElder ? 'இன்றைய மின் சேமிப்பு' : 'Today\'s Electricity Savings',
                    style: TextStyle(
                      fontSize: isElder ? 18 : 14,
                      fontWeight: FontWeight.bold,
                      color: Colors.white70,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    '₹ ${savedAmount.toStringAsFixed(2)}',
                    style: TextStyle(
                      fontSize: isElder ? 42 : 36,
                      fontWeight: FontWeight.w900,
                      color: Colors.white,
                      letterSpacing: -0.5,
                    ),
                  ),
                  Text(
                    '${savingsPercent.toStringAsFixed(0)}% Reduction in Daily Bill',
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: Colors.greenAccent,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),

            // Side-by-Side Comparison Cards
            Row(
              children: [
                // Without Solar (Standard EB)
                Expanded(
                  child: Container(
                    padding: EdgeInsets.all(isElder ? 16 : 12),
                    decoration: BoxDecoration(
                      color: isElder ? Colors.white : Theme.of(context).cardTheme.color,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: Colors.redAccent.withOpacity(0.5), width: 1.5),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Without Solar\n(Standard EB)',
                          style: TextStyle(fontWeight: FontWeight.bold, color: Colors.redAccent),
                        ),
                        const SizedBox(height: 10),
                        Text(
                          '₹ ${standardBill.toStringAsFixed(2)}',
                          style: TextStyle(
                            fontSize: isElder ? 24 : 20,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${usage.totalUnitsToday.toStringAsFixed(1)} Units from Grid',
                          style: TextStyle(fontSize: isElder ? 13 : 11, color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                // With SEMS Smart AI
                Expanded(
                  child: Container(
                    padding: EdgeInsets.all(isElder ? 16 : 12),
                    decoration: BoxDecoration(
                      color: isElder ? Colors.white : Theme.of(context).cardTheme.color,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: Colors.green.withOpacity(0.6), width: 2),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'With SEMS AI\n(Solar + Battery)',
                          style: TextStyle(fontWeight: FontWeight.bold, color: Colors.green),
                        ),
                        const SizedBox(height: 10),
                        Text(
                          '₹ ${semsBill.toStringAsFixed(2)}',
                          style: TextStyle(
                            fontSize: isElder ? 24 : 20,
                            fontWeight: FontWeight.w900,
                            color: Colors.green,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Only ${usage.gridUnitsImportedToday.toStringAsFixed(1)} Units from Grid',
                          style: TextStyle(fontSize: isElder ? 13 : 11, color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // ESG Environmental Impact Row (Features 16, 17, 18)
            Row(
              children: [
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981).withOpacity(0.12),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: const Color(0xFF10B981), width: 1.5),
                    ),
                    child: Column(
                      children: [
                        const Text('🌱', style: TextStyle(fontSize: 22)),
                        const SizedBox(height: 4),
                        Text(
                          '${usage.avoidedCo2Kg.toStringAsFixed(1)} kg',
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: Color(0xFF10B981)),
                        ),
                        Text('CO₂ Avoided', style: TextStyle(fontSize: 11, color: isElder ? Colors.black87 : Colors.white70)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0284C7).withOpacity(0.12),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: const Color(0xFF0284C7), width: 1.5),
                    ),
                    child: Column(
                      children: [
                        const Text('☀️', style: TextStyle(fontSize: 22)),
                        const SizedBox(height: 4),
                        Text(
                          '${usage.cleanEnergyIndexPct.toStringAsFixed(0)}%',
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: Color(0xFF0284C7)),
                        ),
                        Text('Clean Energy', style: TextStyle(fontSize: 11, color: isElder ? Colors.black87 : Colors.white70)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF16A34A).withOpacity(0.12),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: const Color(0xFF16A34A), width: 1.5),
                    ),
                    child: Column(
                      children: [
                        const Text('🌲', style: TextStyle(fontSize: 22)),
                        const SizedBox(height: 4),
                        Text(
                          usage.treesPlantedEquivalent.toStringAsFixed(2),
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: Color(0xFF16A34A)),
                        ),
                        Text('Trees Equiv', style: TextStyle(fontSize: 11, color: isElder ? Colors.black87 : Colors.white70)),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Benefit List
            Container(
              padding: EdgeInsets.all(isElder ? 18 : 14),
              decoration: BoxDecoration(
                color: isElder ? Colors.white : Theme.of(context).cardTheme.color,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.white12, width: 1),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isElder ? 'முக்கிய பயன்கள்' : 'Why You Are Saving Money',
                    style: TextStyle(
                      fontSize: isElder ? 17 : 14,
                      fontWeight: FontWeight.bold,
                      color: isElder ? Colors.black : null,
                    ),
                  ),
                  const SizedBox(height: 8),
                  _buildBenefitItem('☀️ Solar powers appliances directly during high-tariff day hours.', isElder),
                  _buildBenefitItem('🔋 Battery charges on free solar surplus and runs at night.', isElder),
                  _buildBenefitItem('⚡ Grid import kept in 0-100 Units free subsidy tier.', isElder),
                  _buildBenefitItem('📉 Avoids entering expensive TNEB ₹8.00/unit slab.', isElder),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBenefitItem(String text, bool isElder) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.check_circle_rounded, color: Colors.green, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                fontSize: isElder ? 15 : 12,
                color: isElder ? Colors.black87 : Colors.white70,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
