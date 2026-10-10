import 'package:flutter/material.dart';
import '../core/localization.dart';

class UsageGauge extends StatelessWidget {
  final double currentUnits;
  final double targetUnits;
  final String slabName;
  final double slabRate;
  final UserAgeMode ageMode;

  const UsageGauge({
    super.key,
    required this.currentUnits,
    this.targetUnits = 25.0,
    required this.slabName,
    required this.slabRate,
    required this.ageMode,
  });

  @override
  Widget build(BuildContext context) {
    final isElder = ageMode == UserAgeMode.elder;
    final progress = (currentUnits / targetUnits).clamp(0.0, 1.0);

    return Container(
      padding: EdgeInsets.all(isElder ? 20 : 16),
      margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: isElder ? Colors.white : Theme.of(context).cardTheme.color,
        borderRadius: BorderRadius.circular(isElder ? 22 : 18),
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
                isElder ? 'இன்றைய யூனிட் பயன்பாடு' : 'Today\'s Unit Gauge',
                style: TextStyle(
                  fontSize: isElder ? 18 : 14,
                  fontWeight: FontWeight.w800,
                  color: isElder ? Colors.black : null,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF0284C7).withOpacity(0.15),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFF0284C7), width: 1),
                ),
                child: Text(
                  slabName,
                  style: TextStyle(
                    fontSize: isElder ? 14 : 12,
                    fontWeight: FontWeight.bold,
                    color: const Color(0xFF0284C7),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          // Circular / Linear Progress representation
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: isElder ? 18 : 12,
              backgroundColor: isElder ? const Color(0xFFE2E8F0) : Colors.white10,
              valueColor: AlwaysStoppedAnimation<Color>(
                progress > 0.8 ? Colors.redAccent : const Color(0xFF10B981),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '${currentUnits.toStringAsFixed(1)} / ${targetUnits.toStringAsFixed(0)} Units',
                style: TextStyle(
                  fontSize: isElder ? 18 : 14,
                  fontWeight: FontWeight.w900,
                  color: isElder ? Colors.black : null,
                ),
              ),
              Text(
                'Rate: ₹${slabRate.toStringAsFixed(2)} / Unit',
                style: TextStyle(
                  fontSize: isElder ? 16 : 13,
                  fontWeight: FontWeight.w700,
                  color: isElder ? const Color(0xFF334155) : Colors.grey,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
