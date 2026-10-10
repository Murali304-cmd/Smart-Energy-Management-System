class ApplianceUsageItem {
  final String id;
  final String nameKey;
  final double wattage; // Watts
  final String icon;
  double hoursUsed;

  ApplianceUsageItem({
    required this.id,
    required this.nameKey,
    required this.wattage,
    required this.icon,
    this.hoursUsed = 0.0,
  });

  /// Units (kWh) = (Watts * Hours) / 1000
  double get unitsConsumed => (wattage * hoursUsed) / 1000.0;

  /// Cost at standard TNEB average rate (approx Rs 4.50)
  double get estimatedCost => unitsConsumed * 4.50;
}

class UsageCalculator {
  /// Default home appliances list for unit calculator
  static List<ApplianceUsageItem> getDefaultAppliances() {
    return [
      ApplianceUsageItem(id: 'ac', nameKey: 'ac_name', wattage: 1500, icon: '❄️', hoursUsed: 4.0),
      ApplianceUsageItem(id: 'fridge', nameKey: 'fridge_name', wattage: 250, icon: '🧊', hoursUsed: 24.0),
      ApplianceUsageItem(id: 'geyser', nameKey: 'geyser_name', wattage: 2000, icon: '🚿', hoursUsed: 1.0),
      ApplianceUsageItem(id: 'tv', nameKey: 'tv_name', wattage: 120, icon: '📺', hoursUsed: 5.0),
      ApplianceUsageItem(id: 'washing', nameKey: 'washing_name', wattage: 500, icon: '🧺', hoursUsed: 1.5),
      ApplianceUsageItem(id: 'fans', nameKey: 'fans_name', wattage: 300, icon: '💨', hoursUsed: 14.0),
    ];
  }

  /// Calculates combined units for all appliances
  static double calculateTotalApplianceUnits(List<ApplianceUsageItem> items) {
    return items.fold(0.0, (sum, item) => sum + item.unitsConsumed);
  }

  /// Calculates total cost for all appliances
  static double calculateTotalApplianceCost(List<ApplianceUsageItem> items) {
    return items.fold(0.0, (sum, item) => sum + item.estimatedCost);
  }
}
