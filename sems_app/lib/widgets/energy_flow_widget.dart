import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../models/dashboard_model.dart';
import '../core/theme.dart';

class EnergyFlowWidget extends StatefulWidget {
  final DashboardModel data;

  const EnergyFlowWidget({super.key, required this.data});

  @override
  State<EnergyFlowWidget> createState() => _EnergyFlowWidgetState();
}

class _EnergyFlowWidgetState extends State<EnergyFlowWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _animController;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1600),
    )..repeat();
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final solarKw = widget.data.solarKw;
    final loadKw = widget.data.loadKw;
    final batteryPowerKw = widget.data.batteryPowerKw;
    final isDischarging = widget.data.batteryMode == 'discharging' && batteryPowerKw > 0.05;
    final isCharging = widget.data.batteryMode == 'charging' && batteryPowerKw > 0.05;
    final gridKw = widget.data.gridPowerKw;
    final gridExportKw = widget.data.gridExportKw;
    final isGridImport = gridKw > 0.05;
    final isGridExport = gridExportKw > 0.05;
    final soc = widget.data.batterySoc;

    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Theme.of(context).colorScheme.surface,
              Theme.of(context).colorScheme.surfaceContainerHighest.withOpacity(0.35),
            ],
          ),
        ),
        child: Column(
          children: [
            // Header Bar
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(Icons.hub_rounded, color: AppColors.primary, size: 22),
                    const SizedBox(width: 8),
                    Text(
                      'Live Energy Flow',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981).withOpacity(0.15),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFF10B981), width: 1),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: const BoxDecoration(
                          shape: BoxShape.circle,
                          color: Color(0xFF10B981),
                        ),
                      ),
                      const SizedBox(width: 6),
                      const Text(
                        'FLOW ACTIVE',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF10B981),
                          letterSpacing: 0.5,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Animated Energy Flow Diagram with Real-Time Animated Conduits
            AnimatedBuilder(
              animation: _animController,
              builder: (context, _) {
                return LayoutBuilder(
                  builder: (context, constraints) {
                    final width = constraints.maxWidth;
                    const double canvasHeight = 280.0;
                    final centerX = width / 2;
                    final centerY = canvasHeight / 2;

                    // Node Dimensions
                    final sideNodeWidth = (width < 360) ? 92.0 : 100.0;
                    const sideNodeHeight = 60.0;
                    const centerNodeWidth = 110.0;
                    const centerNodeHeight = 58.0;

                    // Node centers
                    final solarCenter = Offset(centerX, 30.0);
                    final homeCenter = Offset(centerX, canvasHeight - 30.0);
                    final batteryCenter = Offset(sideNodeWidth / 2 + 8, centerY);
                    final gridCenter = Offset(width - sideNodeWidth / 2 - 8, centerY);
                    final hubCenter = Offset(centerX, centerY);

                    return SizedBox(
                      width: width,
                      height: canvasHeight,
                      child: Stack(
                        clipBehavior: Clip.none,
                        children: [
                          // 1. Custom Animated Electron / Energy Particle Flow Painter
                          Positioned.fill(
                            child: CustomPaint(
                              painter: _EnergyFlowPainter(
                                progress: _animController.value,
                                hubCenter: hubCenter,
                                solarCenter: solarCenter,
                                homeCenter: homeCenter,
                                batteryCenter: batteryCenter,
                                gridCenter: gridCenter,
                                isSolarActive: solarKw > 0.05,
                                isBatteryCharging: isCharging,
                                isBatteryDischarging: isDischarging,
                                isGridImporting: isGridImport,
                                isGridExporting: isGridExport,
                                isDark: Theme.of(context).brightness == Brightness.dark,
                              ),
                            ),
                          ),

                          // 2. Center Dynamic Microgrid Junction Hub
                          Positioned(
                            left: centerX - 24,
                            top: centerY - 24,
                            child: Container(
                              width: 48,
                              height: 48,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: Theme.of(context).colorScheme.surface,
                                border: Border.all(
                                  color: AppColors.primary,
                                  width: 2.5,
                                ),
                                boxShadow: [
                                  BoxShadow(
                                    color: AppColors.primary.withOpacity(0.35),
                                    blurRadius: 10,
                                    spreadRadius: 2,
                                  )
                                ],
                              ),
                              child: Transform.rotate(
                                angle: _animController.value * 2 * math.pi,
                                child: const Icon(
                                  Icons.autorenew_rounded,
                                  color: AppColors.primary,
                                  size: 26,
                                ),
                              ),
                            ),
                          ),

                          // 3. Top Node: Solar PV
                          Positioned(
                            left: centerX - centerNodeWidth / 2,
                            top: 4,
                            child: _buildNodeCard(
                              title: 'Solar PV',
                              value: '${solarKw.toStringAsFixed(2)} kW',
                              icon: Icons.wb_sunny_rounded,
                              color: const Color(0xFFF59E0B),
                              width: centerNodeWidth,
                              height: centerNodeHeight,
                              isActive: solarKw > 0.05,
                            ),
                          ),

                          // 4. Left Node: Battery Storage
                          Positioned(
                            left: 6,
                            top: centerY - sideNodeHeight / 2,
                            child: _buildNodeCard(
                              title: 'Battery (${soc.toStringAsFixed(0)}%)',
                              value: isCharging
                                  ? '+${batteryPowerKw.toStringAsFixed(2)} kW'
                                  : (isDischarging
                                      ? '-${batteryPowerKw.toStringAsFixed(2)} kW'
                                      : 'Idle'),
                              icon: Icons.battery_charging_full_rounded,
                              color: isCharging
                                  ? const Color(0xFF10B981)
                                  : (isDischarging ? const Color(0xFF38BDF8) : Colors.grey),
                              width: sideNodeWidth,
                              height: sideNodeHeight,
                              isActive: isCharging || isDischarging,
                            ),
                          ),

                          // 5. Right Node: Utility Grid
                          Positioned(
                            right: 6,
                            top: centerY - sideNodeHeight / 2,
                            child: _buildNodeCard(
                              title: 'Utility Grid',
                              value: isGridImport
                                  ? 'Imp ${gridKw.toStringAsFixed(2)} kW'
                                  : (isGridExport
                                      ? 'Exp ${gridExportKw.toStringAsFixed(2)} kW'
                                      : '0.00 kW'),
                              icon: Icons.electrical_services_rounded,
                              color: isGridImport
                                  ? const Color(0xFF818CF8)
                                  : (isGridExport ? const Color(0xFF06B6D4) : Colors.grey),
                              width: sideNodeWidth,
                              height: sideNodeHeight,
                              isActive: isGridImport || isGridExport,
                            ),
                          ),

                          // 6. Bottom Node: Smart Home Load
                          Positioned(
                            left: centerX - centerNodeWidth / 2,
                            bottom: 4,
                            child: _buildNodeCard(
                              title: 'Home Load',
                              value: '${loadKw.toStringAsFixed(2)} kW',
                              icon: Icons.home_rounded,
                              color: const Color(0xFFF97316),
                              width: centerNodeWidth,
                              height: centerNodeHeight,
                              isActive: loadKw > 0.05,
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                );
              },
            ),

            const SizedBox(height: 12),

            // Live Strategy Status Badge
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primary.withOpacity(0.08),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: Theme.of(context).colorScheme.primary.withOpacity(0.25),
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.auto_awesome_rounded, color: AppColors.primary, size: 18),
                  const SizedBox(width: 8),
                  Text(
                    'Optimization Strategy: ${widget.data.strategy}',
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                      color: AppColors.primary,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildNodeCard({
    required String title,
    required String value,
    required IconData icon,
    required Color color,
    required double width,
    required double height,
    required bool isActive,
  }) {
    return Container(
      width: width,
      height: height,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(isActive ? 0.14 : 0.06),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isActive ? color : color.withOpacity(0.3),
          width: isActive ? 1.8 : 1.0,
        ),
        boxShadow: isActive
            ? [
                BoxShadow(
                  color: color.withOpacity(0.2),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                )
              ]
            : null,
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: color, size: 16),
              const SizedBox(width: 4),
              Flexible(
                child: Text(
                  title,
                  style: TextStyle(
                    fontSize: 10.5,
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: TextStyle(
              fontSize: 12.5,
              fontWeight: FontWeight.w900,
              color: isActive ? color : Colors.grey,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}

/// Custom Canvas Painter rendering animated glowing conduits & electron flow particles
class _EnergyFlowPainter extends CustomPainter {
  final double progress;
  final Offset hubCenter;
  final Offset solarCenter;
  final Offset homeCenter;
  final Offset batteryCenter;
  final Offset gridCenter;
  final bool isSolarActive;
  final bool isBatteryCharging;
  final bool isBatteryDischarging;
  final bool isGridImporting;
  final bool isGridExporting;
  final bool isDark;

  _EnergyFlowPainter({
    required this.progress,
    required this.hubCenter,
    required this.solarCenter,
    required this.homeCenter,
    required this.batteryCenter,
    required this.gridCenter,
    required this.isSolarActive,
    required this.isBatteryCharging,
    required this.isBatteryDischarging,
    required this.isGridImporting,
    required this.isGridExporting,
    required this.isDark,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final trackColor = isDark ? Colors.white.withOpacity(0.10) : Colors.black.withOpacity(0.08);

    // 1. Draw base conduit track lines
    final trackPaint = Paint()
      ..color = trackColor
      ..strokeWidth = 5.0
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    // Solar -> Hub
    canvas.drawLine(solarCenter, hubCenter, trackPaint);
    // Hub -> Home
    canvas.drawLine(hubCenter, homeCenter, trackPaint);
    // Battery -> Hub
    canvas.drawLine(batteryCenter, hubCenter, trackPaint);
    // Grid -> Hub
    canvas.drawLine(gridCenter, hubCenter, trackPaint);

    // 2. Animate Solar -> Hub and Hub -> Home Flow
    if (isSolarActive) {
      _drawActiveFlow(
        canvas: canvas,
        start: solarCenter,
        end: hubCenter,
        color: const Color(0xFFF59E0B),
        reverse: false,
      );
      _drawActiveFlow(
        canvas: canvas,
        start: hubCenter,
        end: homeCenter,
        color: const Color(0xFFF59E0B),
        reverse: false,
      );
    }

    // 3. Animate Battery Flow
    if (isBatteryCharging) {
      // Solar surplus flowing into Battery: Hub -> Battery
      _drawActiveFlow(
        canvas: canvas,
        start: hubCenter,
        end: batteryCenter,
        color: const Color(0xFF10B981),
        reverse: false,
      );
    } else if (isBatteryDischarging) {
      // Battery powering house: Battery -> Hub -> Home
      _drawActiveFlow(
        canvas: canvas,
        start: batteryCenter,
        end: hubCenter,
        color: const Color(0xFF38BDF8),
        reverse: false,
      );
      _drawActiveFlow(
        canvas: canvas,
        start: hubCenter,
        end: homeCenter,
        color: const Color(0xFF38BDF8),
        reverse: false,
      );
    }

    // 4. Animate Grid Flow
    if (isGridImporting) {
      // Grid supplying home: Grid -> Hub -> Home
      _drawActiveFlow(
        canvas: canvas,
        start: gridCenter,
        end: hubCenter,
        color: const Color(0xFF818CF8),
        reverse: false,
      );
      _drawActiveFlow(
        canvas: canvas,
        start: hubCenter,
        end: homeCenter,
        color: const Color(0xFF818CF8),
        reverse: false,
      );
    } else if (isGridExporting) {
      // Solar excess exported to grid: Hub -> Grid
      _drawActiveFlow(
        canvas: canvas,
        start: hubCenter,
        end: gridCenter,
        color: const Color(0xFF06B6D4),
        reverse: false,
      );
    }
  }

  void _drawActiveFlow({
    required Canvas canvas,
    required Offset start,
    required Offset end,
    required Color color,
    required bool reverse,
  }) {
    // Active glowing conduit line
    final activeLinePaint = Paint()
      ..color = color.withOpacity(0.35)
      ..strokeWidth = 5.0
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawLine(start, end, activeLinePaint);

    // Glowing moving electron particles
    const int particleCount = 4;
    for (int i = 0; i < particleCount; i++) {
      double t = (progress + (i / particleCount)) % 1.0;
      if (reverse) t = 1.0 - t;

      final particlePos = Offset.lerp(start, end, t)!;

      // Outer glow
      final glowPaint = Paint()
        ..color = color.withOpacity(0.45)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4.0);
      canvas.drawCircle(particlePos, 5.0, glowPaint);

      // Core particle
      final corePaint = Paint()..color = Colors.white;
      canvas.drawCircle(particlePos, 2.5, corePaint);
    }
  }

  @override
  bool shouldRepaint(covariant _EnergyFlowPainter oldDelegate) {
    return oldDelegate.progress != progress ||
        oldDelegate.isSolarActive != isSolarActive ||
        oldDelegate.isBatteryCharging != isBatteryCharging ||
        oldDelegate.isBatteryDischarging != isBatteryDischarging ||
        oldDelegate.isGridImporting != isGridImporting ||
        oldDelegate.isGridExporting != isGridExporting;
  }
}
