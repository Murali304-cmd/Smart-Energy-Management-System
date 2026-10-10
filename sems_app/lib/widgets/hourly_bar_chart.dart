import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../core/localization.dart';

class HourlyBarChart extends StatelessWidget {
  final List<double> hourlyUnits;
  final UserAgeMode ageMode;

  const HourlyBarChart({
    super.key,
    required this.hourlyUnits,
    required this.ageMode,
  });

  @override
  Widget build(BuildContext context) {
    final isElder = ageMode == UserAgeMode.elder;
    final currentHour = DateTime.now().hour;

    return Container(
      height: isElder ? 260 : 220,
      padding: EdgeInsets.all(isElder ? 18 : 14),
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
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                isElder ? '24 மணிநேர மின் பயன்பாடு (யூனிட்)' : '24-Hour Usage Breakdown (kWh)',
                style: TextStyle(
                  fontSize: isElder ? 17 : 14,
                  fontWeight: FontWeight.w800,
                  color: isElder ? Colors.black : null,
                ),
              ),
              Text(
                'Now: ${currentHour}:00',
                style: TextStyle(
                  fontSize: isElder ? 15 : 12,
                  fontWeight: FontWeight.bold,
                  color: const Color(0xFF0284C7),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: BarChart(
              BarChartData(
                alignment: BarChartAlignment.spaceAround,
                maxY: 4.0,
                barTouchData: BarTouchData(
                  enabled: true,
                  touchTooltipData: BarTouchTooltipData(
                    getTooltipColor: (_) => const Color(0xFF0F172A),
                    getTooltipItem: (group, groupIndex, rod, rodIndex) {
                      return BarTooltipItem(
                        '${group.x}:00\n${rod.toY.toStringAsFixed(2)} Units',
                        const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                      );
                    },
                  ),
                ),
                titlesData: FlTitlesData(
                  show: true,
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      getTitlesWidget: (value, meta) {
                        final val = value.toInt();
                        if (val % 4 == 0) {
                          return Padding(
                            padding: const EdgeInsets.only(top: 4.0),
                            child: Text(
                              '$val',
                              style: TextStyle(
                                fontSize: isElder ? 13 : 10,
                                fontWeight: FontWeight.bold,
                                color: isElder ? Colors.black87 : Colors.grey,
                              ),
                            ),
                          );
                        }
                        return const SizedBox.shrink();
                      },
                    ),
                  ),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 28,
                      getTitlesWidget: (value, meta) {
                        if (value % 1.0 == 0) {
                          return Text(
                            '${value.toInt()}u',
                            style: TextStyle(
                              fontSize: isElder ? 12 : 10,
                              fontWeight: FontWeight.bold,
                              color: isElder ? Colors.black87 : Colors.grey,
                            ),
                          );
                        }
                        return const SizedBox.shrink();
                      },
                    ),
                  ),
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                ),
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  horizontalInterval: 1.0,
                  getDrawingHorizontalLine: (_) => FlLine(
                    color: isElder ? const Color(0xFFE2E8F0) : Colors.white10,
                    strokeWidth: 1,
                  ),
                ),
                borderData: FlBorderData(show: false),
                barGroups: List.generate(
                  hourlyUnits.length > 24 ? 24 : hourlyUnits.length,
                  (index) {
                    final isCurrent = index == currentHour;
                    final val = hourlyUnits[index];
                    return BarChartGroupData(
                      x: index,
                      barRods: [
                        BarChartRodData(
                          toY: val,
                          color: isCurrent
                              ? const Color(0xFFF59E0B) // Solar amber for current
                              : const Color(0xFF0284C7),
                          width: isElder ? 7 : 6,
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ],
                    );
                  },
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
