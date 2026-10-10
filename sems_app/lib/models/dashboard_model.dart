class DashboardModel {
  final double solarKw;
  final double loadKw;
  final double batterySoc;
  final double batteryPowerKw;
  final String batteryMode;
  final double gridPowerKw;
  final double gridExportKw;
  final String strategy;
  final double estimatedCost;
  final double remainingBudget;
  final double backupHours;
  final double temperature;
  final double irradiance;
  final String xaiSummary;
  final bool isOnline;
  final double batterySoh;
  final int batteryCycles;
  final double netExportKwh;
  final double netCreditInr;
  final double demandKw;
  final String demandStatus;

  DashboardModel({
    required this.solarKw,
    required this.loadKw,
    required this.batterySoc,
    required this.batteryPowerKw,
    required this.batteryMode,
    required this.gridPowerKw,
    required this.gridExportKw,
    required this.strategy,
    required this.estimatedCost,
    required this.remainingBudget,
    required this.backupHours,
    required this.temperature,
    required this.irradiance,
    required this.xaiSummary,
    required this.isOnline,
    this.batterySoh = 98.4,
    this.batteryCycles = 248,
    this.netExportKwh = 3.40,
    this.netCreditInr = 7.65,
    this.demandKw = 2.91,
    this.demandStatus = 'NORMAL',
  });

  factory DashboardModel.fromJson(Map<String, dynamic> json) {
    final live = json['live'] ?? {};
    final rec = json['recommendation'] ?? {};
    final em = json['energy_management'] ?? {};
    final xai = json['xai'] ?? {};
    final battHealth = json['battery_health'] ?? {};
    final netMeter = json['net_metering'] ?? {};
    final demand = json['demand'] ?? {};

    return DashboardModel(
      solarKw: (rec['solar_power'] ?? em['solar_power_kw'] ?? live['solar_power'] ?? 0.0).toDouble(),
      loadKw: (rec['total_power'] ?? em['household_load_kw'] ?? live['energy_usage'] ?? 2.0).toDouble(),
      batterySoc: (live['battery_soc'] ?? rec['battery_soc_after'] ?? 75.0).toDouble(),
      batteryPowerKw: (rec['battery_power'] ?? em['battery_power_kw'] ?? 0.0).toDouble(),
      batteryMode: (rec['battery_mode'] ?? em['battery_mode'] ?? 'idle').toString(),
      gridPowerKw: (rec['grid_power'] ?? em['grid_power_kw'] ?? 0.0).toDouble(),
      gridExportKw: (rec['grid_export'] ?? em['grid_export_kw'] ?? 0.0).toDouble(),
      strategy: (rec['strategy'] ?? em['energy_strategy'] ?? 'SOLAR + BATTERY + GRID').toString(),
      estimatedCost: (rec['estimated_cost'] ?? em['estimated_cost'] ?? 0.0).toDouble(),
      remainingBudget: (rec['remaining_budget'] ?? 20.0).toDouble(),
      backupHours: (rec['estimated_backup_hours'] ?? em['estimated_backup_hours'] ?? 8.5).toDouble(),
      temperature: (live['temperature'] ?? 28.5).toDouble(),
      irradiance: (live['solar_irradiance'] ?? 800.0).toDouble(),
      xaiSummary: (xai['decision_summary'] ?? 'DQN microgrid controller dispatched clean solar & battery first.').toString(),
      isOnline: true,
      batterySoh: (battHealth['soh_pct'] ?? 98.4).toDouble(),
      batteryCycles: (battHealth['cycles_completed'] ?? 248).toInt(),
      netExportKwh: (netMeter['today_exported_kwh'] ?? 3.40).toDouble(),
      netCreditInr: (netMeter['today_credit_inr'] ?? 7.65).toDouble(),
      demandKw: (demand['current_kw'] ?? 2.91).toDouble(),
      demandStatus: (demand['status'] ?? 'NORMAL').toString(),
    );
  }

  factory DashboardModel.mock() {
    return DashboardModel(
      solarKw: 3.80,
      loadKw: 2.10,
      batterySoc: 82.0,
      batteryPowerKw: 1.50,
      batteryMode: 'charging',
      gridPowerKw: 0.0,
      gridExportKw: 0.20,
      strategy: 'SOLAR + BATTERY (SELF-SUFFICIENT)',
      estimatedCost: 169.80,
      remainingBudget: 25.0,
      backupHours: 9.4,
      temperature: 29.5,
      irradiance: 840.0,
      xaiSummary: 'Solar powers 100% of household appliances. Surplus 1.5 kW is charging the battery.',
      isOnline: true,
      batterySoh: 98.4,
      batteryCycles: 248,
      netExportKwh: 3.40,
      netCreditInr: 7.65,
      demandKw: 2.91,
      demandStatus: 'NORMAL',
    );
  }
}
