import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/localization.dart';
import '../providers/user_profile_provider.dart';
import '../providers/energy_provider.dart';
import '../widgets/cost_banner.dart';
import '../widgets/usage_gauge.dart';
import 'export_screen.dart';
import 'tneb_compare_screen.dart';

class UsageScreen extends StatelessWidget {
  const UsageScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<UserProfileProvider>();
    final energy = context.watch<EnergyProvider>();
    final isElder = profile.isElder;
    final lang = profile.language;
    final usage = energy.usage;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Total Amount & Unit Banner
          const CostBanner(),

          // Unit Gauge Progress
          UsageGauge(
            currentUnits: usage.totalUnitsToday,
            targetUnits: 30.0,
            slabName: usage.currentSlabName,
            slabRate: usage.currentSlabRate,
            ageMode: profile.ageMode,
          ),

          // Action Buttons: Share & TNEB Compare
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 6.0),
            child: Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF0284C7),
                      foregroundColor: Colors.white,
                      padding: EdgeInsets.symmetric(vertical: isElder ? 16 : 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    ),
                    icon: const Icon(Icons.share_rounded),
                    label: Text(
                      isElder ? 'பில் பகிர்க (WhatsApp)' : 'Share Bill',
                      style: TextStyle(fontSize: isElder ? 16 : 14, fontWeight: FontWeight.bold),
                    ),
                    onPressed: () {
                      Navigator.push(context, MaterialPageRoute(builder: (_) => const ExportScreen()));
                    },
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFF0284C7),
                      side: const BorderSide(color: Color(0xFF0284C7), width: 1.5),
                      padding: EdgeInsets.symmetric(vertical: isElder ? 16 : 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    ),
                    icon: const Icon(Icons.compare_arrows_rounded),
                    label: Text(
                      isElder ? 'சேமிப்பு ஒப்பீடு' : 'TNEB Compare',
                      style: TextStyle(fontSize: isElder ? 16 : 14, fontWeight: FontWeight.bold),
                    ),
                    onPressed: () {
                      Navigator.push(context, MaterialPageRoute(builder: (_) => const TnebCompareScreen()));
                    },
                  ),
                ),
              ],
            ),
          ),

          // TNEB Slabs Reference Card
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            padding: EdgeInsets.all(isElder ? 18 : 14),
            decoration: BoxDecoration(
              color: isElder ? Colors.white : Theme.of(context).cardTheme.color,
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
                  AppStrings.get('slab_title', lang),
                  style: TextStyle(
                    fontSize: isElder ? 18 : 15,
                    fontWeight: FontWeight.w900,
                    color: isElder ? Colors.black : null,
                  ),
                ),
                const SizedBox(height: 10),
                _buildSlabRow('0 - 100 Units', 'FREE (₹0.00)', 'Government 100 Units Free Subsidy', true, isElder),
                _buildSlabRow('101 - 400 Units', '₹ 4.70 / Unit', 'Standard Domestic Tier', false, isElder),
                _buildSlabRow('401 - 500 Units', '₹ 6.30 / Unit', 'Mid Consumption Tier', false, isElder),
                _buildSlabRow('501 - 600 Units', '₹ 8.40 / Unit', 'High Consumption Tier', false, isElder),
                _buildSlabRow('601 - 800 Units', '₹ 9.45 / Unit', 'Upper Consumption Tier', false, isElder),
                _buildSlabRow('801 - 1000 Units', '₹ 10.50 / Unit', 'Heavy Domestic Tier', false, isElder),
                _buildSlabRow('1000+ Units', '₹ 11.55 / Unit', 'Maximum Tariff Slab', false, isElder),
              ],
            ),
          ),

          // Feature 25: Interactive TNEB Slab Bill Simulator
          TnebSimulatorWidget(isElder: isElder, lang: lang),

          // Hourly Breakdown Table (Hour by Hour units and cost)
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            padding: EdgeInsets.all(isElder ? 18 : 14),
            decoration: BoxDecoration(
              color: isElder ? Colors.white : Theme.of(context).cardTheme.color,
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
                  AppStrings.get('hourly_breakdown', lang),
                  style: TextStyle(
                    fontSize: isElder ? 18 : 15,
                    fontWeight: FontWeight.w900,
                    color: isElder ? Colors.black : null,
                  ),
                ),
                const SizedBox(height: 12),
                Table(
                  columnWidths: const {
                    0: FlexColumnWidth(1.2),
                    1: FlexColumnWidth(1.4),
                    2: FlexColumnWidth(1.4),
                  },
                  border: TableBorder(
                    horizontalInside: BorderSide(
                      color: isElder ? const Color(0xFFCBD5E1) : Colors.white10,
                      width: 1,
                    ),
                  ),
                  children: [
                    TableRow(
                      decoration: BoxDecoration(
                        color: isElder ? const Color(0xFFF1F5F9) : Colors.white.withOpacity(0.05),
                      ),
                      children: [
                        Padding(
                          padding: const EdgeInsets.all(8.0),
                          child: Text(
                            'Hour',
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: isElder ? 16 : 13),
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.all(8.0),
                          child: Text(
                            'Units (kWh)',
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: isElder ? 16 : 13),
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.all(8.0),
                          child: Text(
                            'Cost (₹)',
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: isElder ? 16 : 13),
                          ),
                        ),
                      ],
                    ),
                    ...List.generate(DateTime.now().hour + 1, (h) {
                      final uVal = usage.hourlyUnits[h];
                      final costVal = uVal * 4.50; // estimate
                      return TableRow(
                        children: [
                          Padding(
                            padding: const EdgeInsets.all(8.0),
                            child: Text(
                              '${h.toString().padLeft(2, '0')}:00',
                              style: TextStyle(fontSize: isElder ? 16 : 13, color: isElder ? Colors.black87 : null),
                            ),
                          ),
                          Padding(
                            padding: const EdgeInsets.all(8.0),
                            child: Text(
                              '${uVal.toStringAsFixed(2)} u',
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: isElder ? 16 : 13,
                                color: const Color(0xFF0284C7),
                              ),
                            ),
                          ),
                          Padding(
                            padding: const EdgeInsets.all(8.0),
                            child: Text(
                              '₹ ${costVal.toStringAsFixed(2)}',
                              style: TextStyle(fontSize: isElder ? 16 : 13, color: isElder ? Colors.black87 : null),
                            ),
                          ),
                        ],
                      );
                    }),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // BEE 5-Star Home Energy Audit & LCOE (Enterprise Features 7 & 15)
          Container(
            padding: EdgeInsets.all(isElder ? 20 : 16),
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
                      '📊 BEE 5-Star Energy Audit',
                      style: TextStyle(
                        fontSize: isElder ? 18 : 15,
                        fontWeight: FontWeight.w900,
                        color: isElder ? Colors.black : Colors.white,
                      ),
                    ),
                    const Text('★★★★★', style: TextStyle(color: Color(0xFFF59E0B), fontSize: 18, letterSpacing: 2)),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  'Specific Energy Consumption: 17.5 kWh/m²/yr',
                  style: TextStyle(fontSize: isElder ? 15 : 13, fontWeight: FontWeight.bold, color: Colors.green),
                ),
                Text(
                  'National Benchmark: 92.5 kWh/m²/yr (+81.1% Superior)',
                  style: TextStyle(fontSize: isElder ? 14 : 12, color: isElder ? Colors.black54 : Colors.grey),
                ),
                const SizedBox(height: 6),
                Text(
                  'Levelized Cost (LCOE): ₹ 2.15/kWh vs Grid ₹ 7.50/kWh',
                  style: TextStyle(fontSize: isElder ? 14 : 12, color: const Color(0xFF0284C7), fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  Widget _buildSlabRow(String slab, String rate, String desc, bool isFree, bool isElder) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  slab,
                  style: TextStyle(
                    fontSize: isElder ? 16 : 14,
                    fontWeight: FontWeight.bold,
                    color: isElder ? Colors.black : null,
                  ),
                ),
                Text(
                  desc,
                  style: TextStyle(
                    fontSize: isElder ? 13 : 11,
                    color: isElder ? const Color(0xFF475569) : Colors.grey,
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: isFree ? Colors.green.withOpacity(0.15) : const Color(0xFF0284C7).withOpacity(0.1),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: isFree ? Colors.green : const Color(0xFF0284C7),
                width: 1,
              ),
            ),
            child: Text(
              rate,
              style: TextStyle(
                fontSize: isElder ? 14 : 12,
                fontWeight: FontWeight.bold,
                color: isFree ? Colors.green : const Color(0xFF0284C7),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class TnebSimulatorWidget extends StatefulWidget {
  final bool isElder;
  final AppLanguage lang;

  const TnebSimulatorWidget({
    super.key,
    required this.isElder,
    required this.lang,
  });

  @override
  State<TnebSimulatorWidget> createState() => _TnebSimulatorWidgetState();
}

class _TnebSimulatorWidgetState extends State<TnebSimulatorWidget> {
  double _simulatedUnits = 320.0;

  double _calculateBill(double units) {
    if (units <= 100) return 0.0;
    double bill = 0.0;
    if (units > 100) {
      bill += (units > 400 ? 300 : (units - 100)) * 4.70;
    }
    if (units > 400) {
      bill += (units > 500 ? 100 : (units - 400)) * 6.30;
    }
    if (units > 500) {
      bill += (units > 600 ? 100 : (units - 500)) * 8.40;
    }
    if (units > 600) {
      bill += (units > 800 ? 200 : (units - 600)) * 9.45;
    }
    if (units > 800) {
      bill += (units > 1000 ? 200 : (units - 800)) * 10.50;
    }
    if (units > 1000) {
      bill += (units - 1000) * 11.55;
    }
    return bill;
  }

  String _getSlabBadge(double units) {
    if (units <= 100) return 'FREE Tier';
    if (units <= 400) return 'Tier 2 (₹4.70/u)';
    if (units <= 500) return 'Tier 3 (₹6.30/u)';
    if (units <= 600) return 'Tier 4 (₹8.40/u)';
    if (units <= 800) return 'Tier 5 (₹9.45/u)';
    if (units <= 1000) return 'Tier 6 (₹10.50/u)';
    return 'Tier 7 (₹11.55/u)';
  }

  @override
  Widget build(BuildContext context) {
    final isElder = widget.isElder;
    final totalBill = _calculateBill(_simulatedUnits);
    final dailyEquiv = totalBill / 60.0;
    final subsidySaved = (_simulatedUnits >= 100 ? 100 : _simulatedUnits) * 4.70;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      padding: EdgeInsets.all(isElder ? 18 : 14),
      decoration: BoxDecoration(
        color: isElder ? Colors.white : Theme.of(context).cardTheme.color,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: isElder ? const Color(0xFF64748B) : Colors.white12,
          width: isElder ? 2.0 : 1.0,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'TNEB Slab Simulator',
                style: TextStyle(
                  fontSize: isElder ? 18 : 15,
                  fontWeight: FontWeight.w900,
                  color: isElder ? Colors.black : null,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFF0284C7).withOpacity(0.15),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFF0284C7)),
                ),
                child: Text(
                  _getSlabBadge(_simulatedUnits),
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF0284C7),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '${_simulatedUnits.toInt()} Units / 2 Mo',
                style: TextStyle(
                  fontSize: isElder ? 20 : 17,
                  fontWeight: FontWeight.w900,
                  color: const Color(0xFF0284C7),
                ),
              ),
              Row(
                children: [
                  IconButton(
                    onPressed: () {
                      setState(() {
                        _simulatedUnits = (_simulatedUnits - 50).clamp(0, 1200);
                      });
                    },
                    icon: const Icon(Icons.remove_circle_outline),
                    tooltip: '-50 Units',
                  ),
                  IconButton(
                    onPressed: () {
                      setState(() {
                        _simulatedUnits = (_simulatedUnits + 50).clamp(0, 1200);
                      });
                    },
                    icon: const Icon(Icons.add_circle_outline),
                    tooltip: '+50 Units',
                  ),
                ],
              ),
            ],
          ),
          Slider(
            value: _simulatedUnits,
            min: 0,
            max: 1200,
            divisions: 24,
            activeColor: const Color(0xFF0284C7),
            onChanged: (val) {
              setState(() {
                _simulatedUnits = val;
              });
            },
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: isElder ? const Color(0xFFF8FAFC) : Colors.white.withOpacity(0.04),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                Column(
                  children: [
                    Text(
                      'Bimonthly Bill',
                      style: TextStyle(
                        fontSize: isElder ? 13 : 11,
                        color: isElder ? const Color(0xFF475569) : Colors.grey,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '₹ ${totalBill.toStringAsFixed(2)}',
                      style: TextStyle(
                        fontSize: isElder ? 18 : 15,
                        fontWeight: FontWeight.w900,
                        color: isElder ? Colors.black : Colors.white,
                      ),
                    ),
                  ],
                ),
                Container(height: 30, width: 1, color: Colors.grey.withOpacity(0.3)),
                Column(
                  children: [
                    Text(
                      'Daily Equiv',
                      style: TextStyle(
                        fontSize: isElder ? 13 : 11,
                        color: isElder ? const Color(0xFF475569) : Colors.grey,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '₹ ${dailyEquiv.toStringAsFixed(2)}/d',
                      style: TextStyle(
                        fontSize: isElder ? 18 : 15,
                        fontWeight: FontWeight.w900,
                        color: const Color(0xFF0284C7),
                      ),
                    ),
                  ],
                ),
                Container(height: 30, width: 1, color: Colors.grey.withOpacity(0.3)),
                Column(
                  children: [
                    Text(
                      'Subsidy Saved',
                      style: TextStyle(
                        fontSize: isElder ? 13 : 11,
                        color: isElder ? const Color(0xFF475569) : Colors.grey,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '₹ ${subsidySaved.toStringAsFixed(0)}',
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w900,
                        color: Colors.green,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
