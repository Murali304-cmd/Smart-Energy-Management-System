class EnergyUsageModel {
  final List<double> hourlyUnits;
  final double currentHourUnits;
  final double totalUnitsToday;
  final double solarUnitsToday;
  final double batteryUnitsDischargedToday;
  final double gridUnitsImportedToday;
  final double totalAmountToday;
  final double moneySavedToday;
  final double currentSlabRate;
  final String currentSlabName;
  final DateTime timestamp;

  EnergyUsageModel({
    required this.hourlyUnits,
    required this.currentHourUnits,
    required this.totalUnitsToday,
    required this.solarUnitsToday,
    required this.batteryUnitsDischargedToday,
    required this.gridUnitsImportedToday,
    required this.totalAmountToday,
    required this.moneySavedToday,
    required this.currentSlabRate,
    required this.currentSlabName,
    required this.timestamp,
  });

  /// Calculates TNEB slab rate and exact cost in INR for a given unit consumption.
  /// Current Official TANGEDCO / TNEB Domestic Tariff Structure (LT-IA Telescopic):
  /// - 0 to 100 units: FREE (₹0.00 Government Subsidy)
  /// - 101 to 400 units: ₹4.70 per unit
  /// - 401 to 500 units: ₹6.30 per unit
  /// - 501 to 600 units: ₹8.40 per unit
  /// - 601 to 800 units: ₹9.45 per unit
  /// - 801 to 1000 units: ₹10.50 per unit
  /// - Above 1000 units: ₹11.55 per unit
  static Map<String, dynamic> calculateTnebBill(double units) {
    if (units <= 0) {
      return {'amount': 0.0, 'slab': 'Free Tier (0-100 Units)', 'rate': 0.0};
    }

    double bill = 0.0;
    String slab = 'Free Tier (0-100 Units)';
    double rate = 0.0;

    if (units <= 100) {
      bill = 0.0;
      slab = '100 Units Free Subsidy';
      rate = 0.0;
    } else if (units <= 400) {
      bill = (units - 100) * 4.70;
      slab = 'Slab 2 (101-400 Units @ ₹4.70)';
      rate = 4.70;
    } else if (units <= 500) {
      bill = (300 * 4.70) + ((units - 400) * 6.30);
      slab = 'Slab 3 (401-500 Units @ ₹6.30)';
      rate = 6.30;
    } else if (units <= 600) {
      bill = (300 * 4.70) + (100 * 6.30) + ((units - 500) * 8.40);
      slab = 'Slab 4 (501-600 Units @ ₹8.40)';
      rate = 8.40;
    } else if (units <= 800) {
      bill = (300 * 4.70) + (100 * 6.30) + (100 * 8.40) + ((units - 600) * 9.45);
      slab = 'Slab 5 (601-800 Units @ ₹9.45)';
      rate = 9.45;
    } else if (units <= 1000) {
      bill = (300 * 4.70) + (100 * 6.30) + (100 * 8.40) + (200 * 9.45) + ((units - 800) * 10.50);
      slab = 'Slab 6 (801-1000 Units @ ₹10.50)';
      rate = 10.50;
    } else {
      bill = (300 * 4.70) + (100 * 6.30) + (100 * 8.40) + (200 * 9.45) + (200 * 10.50) + ((units - 1000) * 11.55);
      slab = 'Slab 7 (1000+ Units @ ₹11.55)';
      rate = 11.55;
    }

    return {
      'amount': bill,
      'slab': slab,
      'rate': rate,
    };
  }

  /// Daily TNEB pro-rated bill calculation (pro-rating the 60-day cycle for accurate 1-day cost)
  static Map<String, dynamic> calculateTnebDailyBill(double units) {
    if (units <= 0) {
      return {'amount': 0.0, 'slab': '100 Units Free Subsidy', 'rate': 0.0};
    }
    // Pro-rate 60-day bi-monthly billing: ~1.67 units/day free
    const dailyFreeQuota = 100.0 / 60.0; // 1.67 units/day free
    if (units <= dailyFreeQuota) {
      return {'amount': 0.0, 'slab': 'Free Subsidy (Daily Allowance)', 'rate': 0.0};
    }

    final billableUnits = units - dailyFreeQuota;
    final amount = billableUnits * 4.70;
    return {
      'amount': amount,
      'slab': 'TNEB LT-IA: Tier 2 (₹4.70/kWh)',
      'rate': 4.70,
    };
  }

  factory EnergyUsageModel.createMock({double currentLoadKw = 2.1, double solarKw = 3.5}) {
    final now = DateTime.now();
    final List<double> mockHours = [];
    double total = 0.0;
    double solarTotal = 0.0;
    double gridTotal = 0.0;

    // Simulate past 24 hours of units (kWh)
    for (int h = 0; h <= now.hour; h++) {
      double baseLoad = (h >= 6 && h <= 9) ? 2.4 : ((h >= 17 && h <= 22) ? 2.8 : 1.2);
      double sKw = (h >= 6 && h <= 18) ? (3.8 * (h < 12 ? (h - 6) / 6.0 : (18 - h) / 6.0)) : 0.0;
      double unitsThisHour = baseLoad * 0.9;
      mockHours.add(unitsThisHour);
      total += unitsThisHour;
      solarTotal += sKw;
      gridTotal += (unitsThisHour > sKw) ? (unitsThisHour - sKw) : 0.0;
    }

    // Fill remaining hours with 0.0
    while (mockHours.length < 24) {
      mockHours.add(0.0);
    }

    final billInfo = calculateTnebDailyBill(gridTotal);
    final standardWithoutSolar = calculateTnebDailyBill(total);
    final saved = (standardWithoutSolar['amount'] as double) - (billInfo['amount'] as double);

    return EnergyUsageModel(
      hourlyUnits: mockHours,
      currentHourUnits: mockHours[now.hour],
      totalUnitsToday: total,
      solarUnitsToday: solarTotal,
      batteryUnitsDischargedToday: 3.5,
      gridUnitsImportedToday: gridTotal,
      totalAmountToday: billInfo['amount'] as double,
      moneySavedToday: saved > 0 ? saved : (solarTotal * 4.70),
      currentSlabRate: billInfo['rate'] as double,
      currentSlabName: billInfo['slab'] as String,
      timestamp: now,
    );
  }

  /// ESG Carbon Accounting Metrics (Features 16, 17, 18)
  double get avoidedCo2Kg => solarUnitsToday * 0.92;
  double get cleanEnergyIndexPct => totalUnitsToday > 0 ? (solarUnitsToday / totalUnitsToday * 100).clamp(0.0, 100.0) : 85.0;
  double get treesPlantedEquivalent => (solarUnitsToday * 0.92) / 21.77;
}
