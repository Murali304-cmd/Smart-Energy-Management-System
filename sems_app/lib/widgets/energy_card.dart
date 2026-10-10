import 'package:flutter/material.dart';
import '../core/localization.dart';

class EnergyCard extends StatelessWidget {
  final String title;
  final String value;
  final String subtext;
  final IconData icon;
  final Color color;
  final UserAgeMode ageMode;
  final String? elderTitle;

  const EnergyCard({
    super.key,
    required this.title,
    required this.value,
    required this.subtext,
    required this.icon,
    required this.color,
    required this.ageMode,
    this.elderTitle,
  });

  @override
  Widget build(BuildContext buildContext) {
    final isElder = ageMode == UserAgeMode.elder;
    final displayTitle = (isElder && elderTitle != null) ? elderTitle! : title;

    return Container(
      padding: EdgeInsets.all(isElder ? 18.0 : 14.0),
      decoration: BoxDecoration(
        color: isElder ? Colors.white : Theme.of(buildContext).cardTheme.color,
        borderRadius: BorderRadius.circular(isElder ? 18 : 16),
        border: Border.all(
          color: isElder ? const Color(0xFF64748B) : color.withOpacity(0.35),
          width: isElder ? 2.0 : 1.2,
        ),
        boxShadow: [
          BoxShadow(
            color: color.withOpacity(isElder ? 0.05 : 0.12),
            blurRadius: isElder ? 4 : 10,
            offset: const Offset(0, 3),
          )
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  displayTitle,
                  style: TextStyle(
                    fontSize: isElder ? 17 : 13,
                    fontWeight: isElder ? FontWeight.w800 : FontWeight.w600,
                    color: isElder ? Colors.black87 : Theme.of(buildContext).textTheme.bodyMedium?.color,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Container(
                padding: EdgeInsets.all(isElder ? 10 : 8),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.15),
                  shape: BoxShape.circle,
                ),
                child: Icon(icon, color: color, size: isElder ? 30 : 22),
              ),
            ],
          ),
          const Spacer(),
          Text(
            value,
            style: TextStyle(
              fontSize: isElder ? 28 : 22,
              fontWeight: FontWeight.w900,
              color: isElder ? Colors.black : color,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            subtext,
            style: TextStyle(
              fontSize: isElder ? 15 : 12,
              fontWeight: isElder ? FontWeight.w700 : FontWeight.w500,
              color: isElder ? const Color(0xFF334155) : Theme.of(buildContext).textTheme.bodySmall?.color,
            ),
          ),
        ],
      ),
    );
  }
}
