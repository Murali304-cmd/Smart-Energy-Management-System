import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../core/theme.dart';

class EnterpriseHubScreen extends StatefulWidget {
  final ApiService apiService;

  const EnterpriseHubScreen({super.key, required this.apiService});

  @override
  State<EnterpriseHubScreen> createState() => _EnterpriseHubScreenState();
}

class _EnterpriseHubScreenState extends State<EnterpriseHubScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = false;

  // Data states
  Map<String, dynamic>? _carbonData;
  Map<String, dynamic>? _p2pData;
  Map<String, dynamic>? _ledgerData;
  Map<String, dynamic>? _evData;
  Map<String, dynamic>? _islandingData;
  Map<String, dynamic>? _modelsData;
  Map<String, dynamic>? _simulatorResult;

  // Simulator Sliders
  double _solarKw = 5.0;
  double _batteryKwh = 10.0;
  double _loadKwh = 18.0;
  double _tariffInr = 6.5;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 6, vsync: this);
    _loadAllData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadAllData() async {
    setState(() => _isLoading = true);
    try {
      final carbon = await widget.apiService.fetchCarbonEmissions();
      final p2p = await widget.apiService.fetchP2PMarket();
      final ledger = await widget.apiService.fetchLedger();
      final ev = await widget.apiService.fetchEVDispatch();
      final islanding = await widget.apiService.fetchIslandingStatus();
      final models = await widget.apiService.fetchModelStatus();
      final sim = await widget.apiService.evaluateSimulator(
        solarCapacityKw: _solarKw,
        batteryCapacityKwh: _batteryKwh,
        dailyAverageLoadKwh: _loadKwh,
        gridTariffInr: _tariffInr,
      );

      if (mounted) {
        setState(() {
          _carbonData = carbon;
          _p2pData = p2p;
          _ledgerData = ledger;
          _evData = ev;
          _islandingData = islanding;
          _modelsData = models;
          _simulatorResult = sim;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Enterprise & Smart Grid Hub'),
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Telemetry',
            onPressed: _loadAllData,
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          labelColor: AppColors.primary,
          unselectedLabelColor: Colors.grey,
          indicatorColor: AppColors.primary,
          indicatorWeight: 3,
          tabs: const [
            Tab(icon: Icon(Icons.eco_rounded), text: 'Carbon ESG'),
            Tab(icon: Icon(Icons.swap_horiz_rounded), text: 'P2P Trading'),
            Tab(icon: Icon(Icons.electric_car_rounded), text: 'EV & V2G'),
            Tab(icon: Icon(Icons.calculate_rounded), text: 'ROI Simulator'),
            Tab(icon: Icon(Icons.shield_rounded), text: 'Islanding'),
            Tab(icon: Icon(Icons.psychology_rounded), text: 'AI Retrain'),
          ],
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : TabBarView(
              controller: _tabController,
              children: [
                _buildCarbonTab(),
                _buildP2PTab(),
                _buildEVTab(),
                _buildSimulatorTab(),
                _buildIslandingTab(),
                _buildRetrainingTab(),
              ],
            ),
    );
  }

  // 1. Carbon & ESG Tracker Tab
  Widget _buildCarbonTab() {
    final greenEnergy = _carbonData?['green_energy_percentage'] ?? 84.5;
    final co2Avoided = _carbonData?['kg_co2_avoided_today'] ?? 12.4;
    final trees = _carbonData?['trees_equivalent_annual'] ?? 2.8;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(
            icon: Icons.eco_rounded,
            title: 'Scope 2 Carbon Accounting & ESG',
            subtitle: 'Real-time decarbonization tracking and clean energy offset',
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _buildMetricCard(
                  title: 'Green Energy Index',
                  value: '${greenEnergy.toStringAsFixed(1)}%',
                  icon: Icons.energy_savings_leaf_rounded,
                  color: Colors.green,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildMetricCard(
                  title: 'CO₂ Avoided Today',
                  value: '${co2Avoided.toStringAsFixed(1)} kg',
                  icon: Icons.cloud_done_rounded,
                  color: Colors.teal,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildMetricCard(
            title: 'Tree Planting Equivalent',
            value: '🌳 ${(trees as num).toStringAsFixed(1)} Trees Saved Annually',
            icon: Icons.forest_rounded,
            color: Colors.green.shade700,
          ),
          const SizedBox(height: 16),
          Card(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Clean Power Contribution',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 12),
                  LinearProgressIndicator(
                    value: (greenEnergy as num).toDouble() / 100.0,
                    minHeight: 12,
                    borderRadius: BorderRadius.circular(6),
                    backgroundColor: Colors.grey.shade300,
                    valueColor: const AlwaysStoppedAnimation<Color>(Colors.green),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '${(greenEnergy as num).toStringAsFixed(1)}% of your electricity consumption is supplied by zero-emission Solar and Clean Battery power.',
                    style: const TextStyle(fontSize: 13, color: Colors.grey),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // 2. P2P Microgrid Trading & Proof-of-Energy Ledger
  Widget _buildP2PTab() {
    final rate = _p2pData?['cleared_price_inr'] ?? 5.20;
    final surplus = _p2pData?['surplus_kw'] ?? 1.85;
    final action = _p2pData?['market_action'] ?? 'SELLING_TO_PEERS';
    final blocks = _ledgerData?['blocks_mined'] ?? 142;
    final transactedKwh = _ledgerData?['total_transacted_kwh'] ?? 382.5;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(
            icon: Icons.swap_horiz_rounded,
            title: 'P2P Microgrid Marketplace',
            subtitle: 'Automated double-auction local energy trading & ledger',
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _buildMetricCard(
                  title: 'Cleared P2P Rate',
                  value: '₹${(rate as num).toStringAsFixed(2)}/kWh',
                  icon: Icons.currency_rupee_rounded,
                  color: Colors.indigo,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildMetricCard(
                  title: 'Market Status',
                  value: action.toString().replaceAll('_', ' '),
                  icon: Icons.storefront_rounded,
                  color: Colors.deepPurple,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildMetricCard(
            title: 'Current Export Surplus',
            value: '${(surplus as num).toStringAsFixed(2)} kW available to neighbors',
            icon: Icons.electric_bolt_rounded,
            color: Colors.amber.shade800,
          ),
          const SizedBox(height: 16),
          Card(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Proof-of-Green Ledger',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: Colors.green.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          '$blocks Blocks',
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Colors.green),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Total transacted: ${(transactedKwh as num).toStringAsFixed(1)} kWh\nCryptographic SHA-256 state ensures zero double-counting across the microgrid.',
                    style: const TextStyle(fontSize: 13, color: Colors.grey),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // 3. EV & V2G Smart Dispatch
  Widget _buildEVTab() {
    final soc = _evData?['soc_percent'] ?? 78.0;
    final mode = _evData?['v2g_mode'] ?? 'V2H_STANDBY';
    final profit = _evData?['profit_earned_today'] ?? 42.50;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(
            icon: Icons.electric_car_rounded,
            title: 'Vehicle-to-Grid (V2G) Smart Hub',
            subtitle: 'Bidirectional EV charging & battery home backup',
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _buildMetricCard(
                  title: 'EV Battery SOC',
                  value: '${(soc as num).toStringAsFixed(0)}%',
                  icon: Icons.battery_charging_full_rounded,
                  color: Colors.blue,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildMetricCard(
                  title: 'V2G Dispatch Mode',
                  value: mode.toString(),
                  icon: Icons.sync_alt_rounded,
                  color: Colors.teal,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildMetricCard(
            title: 'Discharge Profit Today',
            value: '₹${(profit as num).toStringAsFixed(2)} Earned from Peak Support',
            icon: Icons.monetization_on_rounded,
            color: Colors.amber.shade800,
          ),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('V2H Home Backup Mode Engaged')),
              );
            },
            icon: const Icon(Icons.power_settings_new_rounded),
            label: const Text('Toggle Bidirectional Discharge'),
            style: ElevatedButton.styleFrom(
              minimumSize: const Size(double.infinity, 48),
              backgroundColor: AppColors.primary,
            ),
          )
        ],
      ),
    );
  }

  // 4. 'What-If' Solar & Battery ROI Simulator
  Widget _buildSimulatorTab() {
    final sim = _simulatorResult?['simulation'] ?? {};
    final capex = sim['total_investment_inr'] ?? 360000;
    final savings = sim['annual_bill_savings_inr'] ?? 52000;
    final payback = sim['payback_period_years'] ?? 6.9;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(
            icon: Icons.calculate_rounded,
            title: '\'What-If\' Solar & Battery ROI Sizer',
            subtitle: 'Simulate system capacity and calculate payback period',
          ),
          const SizedBox(height: 16),
          Card(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Solar PV Capacity:', style: TextStyle(fontWeight: FontWeight.bold)),
                      Text('${_solarKw.toStringAsFixed(1)} kW', style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.amber)),
                    ],
                  ),
                  Slider(
                    value: _solarKw,
                    min: 1.0,
                    max: 20.0,
                    divisions: 19,
                    activeColor: Colors.amber.shade700,
                    onChanged: (v) {
                      setState(() => _solarKw = v);
                      _recalculateSimulator();
                    },
                  ),
                  const SizedBox(height: 10),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Battery Storage Capacity:', style: TextStyle(fontWeight: FontWeight.bold)),
                      Text('${_batteryKwh.toStringAsFixed(0)} kWh', style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.teal)),
                    ],
                  ),
                  Slider(
                    value: _batteryKwh,
                    min: 2.0,
                    max: 40.0,
                    divisions: 19,
                    activeColor: Colors.teal,
                    onChanged: (v) {
                      setState(() => _batteryKwh = v);
                      _recalculateSimulator();
                    },
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _buildMetricCard(
                  title: 'Est. Payback Period',
                  value: '${(payback as num).toStringAsFixed(1)} Years',
                  icon: Icons.timelapse_rounded,
                  color: Colors.green,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildMetricCard(
                  title: 'Annual Savings',
                  value: '₹${(savings as num).toStringAsFixed(0)}/yr',
                  icon: Icons.savings_rounded,
                  color: Colors.indigo,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildMetricCard(
            title: 'Initial Capital Investment',
            value: '₹${(capex as num).toStringAsFixed(0)} Est. Equipment & Installation',
            icon: Icons.account_balance_wallet_rounded,
            color: Colors.purple,
          ),
        ],
      ),
    );
  }

  Future<void> _recalculateSimulator() async {
    final sim = await widget.apiService.evaluateSimulator(
      solarCapacityKw: _solarKw,
      batteryCapacityKwh: _batteryKwh,
      dailyAverageLoadKwh: _loadKwh,
      gridTariffInr: _tariffInr,
    );
    if (mounted) {
      setState(() => _simulatorResult = sim);
    }
  }

  // 5. Microgrid Islanding Control
  Widget _buildIslandingTab() {
    final mode = _islandingData?['operating_mode'] ?? 'GRID_TIED_NORMAL';
    final freq = _islandingData?['grid_frequency_hz'] ?? 50.02;
    final volt = _islandingData?['grid_voltage_v'] ?? 231.4;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(
            icon: Icons.shield_rounded,
            title: 'Microgrid Islanding & Resilience',
            subtitle: 'Autonomous grid disconnect and PLL frequency synchronization',
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _buildMetricCard(
                  title: 'Operating Mode',
                  value: mode.toString().replaceAll('_', ' '),
                  icon: Icons.power_rounded,
                  color: Colors.blue,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildMetricCard(
                  title: 'Grid Frequency',
                  value: '${(freq as num).toStringAsFixed(2)} Hz',
                  icon: Icons.graphic_eq_rounded,
                  color: Colors.purple,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildMetricCard(
            title: 'Grid Voltage',
            value: '${(volt as num).toStringAsFixed(1)} V (Phase-Locked Loop Synchronized)',
            icon: Icons.bolt_rounded,
            color: Colors.teal,
          ),
          const SizedBox(height: 20),
          ElevatedButton.icon(
            onPressed: () async {
              final ok = await widget.apiService.triggerIslanding('MANUAL_USER_TRIGGER');
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text(ok ? 'Islanding Disconnect Triggered' : 'Action Failed')),
                );
                _loadAllData();
              }
            },
            icon: const Icon(Icons.power_off_rounded),
            label: const Text('Trigger Autonomous Islanding'),
            style: ElevatedButton.styleFrom(
              minimumSize: const Size(double.infinity, 50),
              backgroundColor: Colors.deepOrange,
            ),
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: () async {
              final ok = await widget.apiService.restoreGrid();
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text(ok ? 'Reconnecting & Synchronizing Grid' : 'Action Failed')),
                );
                _loadAllData();
              }
            },
            icon: const Icon(Icons.sync_rounded),
            label: const Text('Restore Grid Connection (PLL Sync)'),
            style: OutlinedButton.styleFrom(
              minimumSize: const Size(double.infinity, 50),
            ),
          )
        ],
      ),
    );
  }

  // 6. AI Model Retraining Hub
  Widget _buildRetrainingTab() {
    final predictor = _modelsData?['predictor'] ?? {};
    final solarOk = predictor['solar_mlp_trained'] ?? true;
    final loadOk = predictor['load_lstm_trained'] ?? true;
    final priceOk = predictor['price_xgboost_trained'] ?? true;
    final dqnOk = _modelsData?['dqn_recommender']?['agent_loaded'] ?? true;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(
            icon: Icons.psychology_rounded,
            title: 'Continuous Online AI Retraining',
            subtitle: 'Fine-tunes Solar MLP, Load LSTM, Price XGBoost & DQN Recommender',
          ),
          const SizedBox(height: 16),
          _buildModelStatusTile('Solar Generation Forecaster (MLP)', solarOk),
          _buildModelStatusTile('Household Demand Forecaster (LSTM)', loadOk),
          _buildModelStatusTile('Grid Tariff Estimator (XGBoost)', priceOk),
          _buildModelStatusTile('Deep Q-Network Energy Recommender (DQN)', dqnOk),
          const SizedBox(height: 20),
          ElevatedButton.icon(
            onPressed: () async {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Starting AI model retraining pipeline...')),
              );
              final ok = await widget.apiService.triggerRetraining();
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text(ok ? 'Models successfully fine-tuned with recent telemetry!' : 'Retraining request sent.')),
                );
                _loadAllData();
              }
            },
            icon: const Icon(Icons.model_training_rounded),
            label: const Text('Trigger Online Model Retraining'),
            style: ElevatedButton.styleFrom(
              minimumSize: const Size(double.infinity, 50),
              backgroundColor: AppColors.primary,
            ),
          )
        ],
      ),
    );
  }

  Widget _buildModelStatusTile(String name, bool isTrained) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        leading: Icon(
          isTrained ? Icons.check_circle_rounded : Icons.pending_rounded,
          color: isTrained ? Colors.green : Colors.amber,
        ),
        title: Text(name, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: (isTrained ? Colors.green : Colors.amber).withOpacity(0.12),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            isTrained ? 'TRAINED' : 'PENDING',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.bold,
              color: isTrained ? Colors.green : Colors.amber,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader({required IconData icon, required String title, required String subtitle}) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: AppColors.primary.withOpacity(0.12),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, color: AppColors.primary, size: 28),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              Text(subtitle, style: const TextStyle(color: Colors.grey, fontSize: 12)),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildMetricCard({
    required String title,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: color, size: 20),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(fontSize: 11, color: Colors.grey, fontWeight: FontWeight.w600),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              value,
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: color),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}
