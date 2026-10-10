import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/localization.dart';
import '../core/theme.dart';
import '../providers/user_profile_provider.dart';
import '../providers/energy_provider.dart';
import '../widgets/cost_banner.dart';
import '../widgets/energy_card.dart';
import '../widgets/hourly_bar_chart.dart';
import '../widgets/energy_flow_widget.dart';
import '../services/tts_service.dart';
import 'enterprise_hub_screen.dart';
import 'usage_screen.dart';
import 'battery_screen.dart';
import 'alerts_screen.dart';
import 'settings_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<UserProfileProvider>();
    final energy = context.watch<EnergyProvider>();
    final lang = profile.language;

    final pages = [
      _buildDashboardView(context, profile, energy),
      const UsageScreen(),
      const BatteryScreen(),
      const SettingsScreen(),
    ];

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              AppStrings.get('app_title', lang),
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w900,
              ),
            ),
            Text(
              AppStrings.get('app_subtitle', lang),
              style: const TextStyle(
                fontSize: 11,
                color: Colors.grey,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
        actions: [
          // Enterprise Hub Icon
          IconButton(
            icon: const Icon(Icons.smart_toy_rounded, color: Colors.amber),
            tooltip: 'AI Energy Copilot',
            onPressed: () => _openCopilotModal(context, energy, lang),
          ),
          IconButton(
            icon: const Icon(Icons.hub_outlined, color: AppColors.primary),
            tooltip: 'Enterprise Hub',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => EnterpriseHubScreen(apiService: energy.apiService),
                ),
              );
            },
          ),
          // Alerts Bell Icon with Badge
          IconButton(
            icon: Badge(
              label: Text('${energy.alerts.length}'),
              child: const Icon(Icons.notifications_outlined),
            ),
            tooltip: AppStrings.get('tab_alerts', lang),
            onPressed: () {
              Navigator.push(context, MaterialPageRoute(builder: (_) => const AlertsScreen()));
            },
          ),
          // Refresh Button
          IconButton(
            icon: energy.isLoading
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.refresh_rounded),
            onPressed: () => energy.refreshData(),
          ),
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 580),
          child: pages[_currentIndex],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          TtsService().speakSummary(
            totalUnits: energy.usage.totalUnitsToday,
            cost: energy.usage.totalAmountToday,
            solarUnits: energy.usage.solarUnitsToday,
            backupHours: energy.dashboard.backupHours,
            language: lang,
          );
        },
        icon: const Icon(Icons.volume_up_rounded),
        label: Text(lang == AppLanguage.tamil ? 'குரல் சுருக்கம்' : 'Voice Summary'),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) => setState(() => _currentIndex = index),
        destinations: [
          NavigationDestination(
            icon: const Icon(Icons.dashboard_rounded),
            label: AppStrings.get('tab_home', lang),
          ),
          NavigationDestination(
            icon: const Icon(Icons.receipt_long_rounded),
            label: AppStrings.get('tab_usage', lang),
          ),
          NavigationDestination(
            icon: const Icon(Icons.battery_charging_full_rounded),
            label: AppStrings.get('tab_battery', lang),
          ),
          NavigationDestination(
            icon: const Icon(Icons.settings_rounded),
            label: AppStrings.get('tab_settings', lang),
          ),
        ],
      ),
    );
  }

  Widget _buildDashboardView(
    BuildContext context,
    UserProfileProvider profile,
    EnergyProvider energy,
  ) {
    final lang = profile.language;
    final d = energy.dashboard;
    final u = energy.usage;

    return RefreshIndicator(
      onRefresh: () => energy.refreshData(),
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SizedBox(height: 6),
            // Primary Requirement Card: 1-Day Total Amount & Units Used Today
            const CostBanner(),

            // Real-Time Animated Energy Flow Visualizer
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 4.0),
              child: EnergyFlowWidget(data: d),
            ),

            // Feature 23: Quick Daily Budget Presets
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
              child: Row(
                children: [
                  Text(
                    lang == AppLanguage.tamil ? 'தினசரி வரவு-செலவு:' : 'Daily Budget:',
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: Colors.grey,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        children: [
                          _buildBudgetChip(context, profile, '₹15 Economy', 15.0),
                          const SizedBox(width: 8),
                          _buildBudgetChip(context, profile, '₹25 Balanced', 25.0),
                          const SizedBox(width: 8),
                          _buildBudgetChip(context, profile, '₹40 Solar Focus', 40.0),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // Strategy Banner
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.white12),
              ),
              child: Row(
                children: [
                  const Icon(Icons.auto_awesome, color: Color(0xFF0284C7), size: 24),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          lang == AppLanguage.tamil ? 'DQN மைக்ரோ கிரிட் வியூகம்' : 'DQN Microgrid Strategy',
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            color: Colors.grey,
                          ),
                        ),
                        Text(
                          d.strategy,
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w900,
                            color: Colors.white,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            // Live 4-Card Energy Flow Grid
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 6.0),
              child: GridView.count(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisCount: 2,
                crossAxisSpacing: 10,
                mainAxisSpacing: 10,
                childAspectRatio: 1.25,
                children: [
                  // 1. Solar
                  EnergyCard(
                    title: AppStrings.get('solar_gen', lang),
                    elderTitle: AppStrings.get('solar_gen_elder', lang),
                    value: '${d.solarKw.toStringAsFixed(2)} kW',
                    subtext: '${u.solarUnitsToday.toStringAsFixed(1)} Units generated',
                    icon: Icons.wb_sunny_rounded,
                    color: AppTheme.solarAmber,
                    ageMode: profile.ageMode,
                  ),

                  // 2. Battery Storage
                  EnergyCard(
                    title: AppStrings.get('battery_stored', lang),
                    elderTitle: AppStrings.get('battery_stored_elder', lang),
                    value: '${d.batterySoc.toStringAsFixed(0)} %',
                    subtext: '${d.backupHours.toStringAsFixed(1)} Hrs backup (${d.batteryMode})',
                    icon: Icons.battery_charging_full_rounded,
                    color: AppTheme.batteryGreen,
                    ageMode: profile.ageMode,
                  ),

                  // 3. Grid Power
                  EnergyCard(
                    title: AppStrings.get('grid_import', lang),
                    elderTitle: AppStrings.get('grid_import_elder', lang),
                    value: '${d.gridPowerKw.toStringAsFixed(2)} kW',
                    subtext: '${u.gridUnitsImportedToday.toStringAsFixed(1)} Units from EB',
                    icon: Icons.electric_bolt_rounded,
                    color: AppTheme.primaryBlue,
                    ageMode: profile.ageMode,
                  ),

                  // 4. Household Demand
                  EnergyCard(
                    title: 'Home Load',
                    elderTitle: 'வீட்டு மின் தேவை',
                    value: '${d.loadKw.toStringAsFixed(2)} kW',
                    subtext: '${u.totalUnitsToday.toStringAsFixed(1)} Total units',
                    icon: Icons.home_rounded,
                    color: AppTheme.gridViolet,
                    ageMode: profile.ageMode,
                  ),
                ],
              ),
            ),

            // Enterprise & Smart Grid Hub Banner
            InkWell(
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => EnterpriseHubScreen(apiService: energy.apiService),
                  ),
                );
              },
              borderRadius: BorderRadius.circular(18),
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  gradient: LinearGradient(
                    colors: [
                      AppColors.primary.withOpacity(0.12),
                      Colors.indigo.withOpacity(0.08),
                    ],
                  ),
                  border: Border.all(color: AppColors.primary.withOpacity(0.3)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.hub_rounded, color: AppColors.primary, size: 22),
                            const SizedBox(width: 8),
                            Text(
                              'Enterprise & Smart Grid Hub',
                              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                    fontWeight: FontWeight.bold,
                                  ),
                            ),
                          ],
                        ),
                        const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: AppColors.primary),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'P2P Trading • Carbon ESG • V2G EV Dispatch • Islanding • ROI Sizer • AI Retraining',
                      style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                    ),
                  ],
                ),
              ),
            ),

            // 24-Hour Usage Breakdown Chart
            HourlyBarChart(
              hourlyUnits: u.hourlyUnits,
              ageMode: profile.ageMode,
            ),

            // XAI Decision Note
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: Colors.white10,
                  width: 1.0,
                ),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.info_outline_rounded, color: Color(0xFF0284C7), size: 24),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      d.xaiSummary,
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                        color: Color(0xFFCBD5E1),
                        height: 1.4,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  Widget _buildBudgetChip(
    BuildContext context,
    UserProfileProvider profile,
    String label,
    double budgetValue,
  ) {
    final isSelected = (profile.userBudget - budgetValue).abs() < 0.01;

    return InkWell(
      onTap: () {
        profile.setBudget(budgetValue);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Daily Budget set to ₹${budgetValue.toStringAsFixed(0)}/day'),
            duration: const Duration(seconds: 1),
            behavior: SnackBarBehavior.floating,
          ),
        );
      },
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: isSelected
              ? const Color(0xFF0284C7)
              : Colors.white.withOpacity(0.08),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected
                ? const Color(0xFF0284C7)
                : Colors.white24,
            width: 1.0,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.bold,
            color: isSelected ? Colors.white : Colors.white70,
          ),
        ),
      ),
    );
  }

  void _openCopilotModal(BuildContext context, EnergyProvider energy, AppLanguage lang) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF0F172A),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) {
        return _CopilotSheetContent(apiService: energy.apiService, lang: lang);
      },
    );
  }
}

class _CopilotSheetContent extends StatefulWidget {
  final ApiService apiService;
  final AppLanguage lang;

  const _CopilotSheetContent({required this.apiService, required this.lang});

  @override
  State<_CopilotSheetContent> createState() => _CopilotSheetContentState();
}

class _CopilotSheetContentState extends State<_CopilotSheetContent> {
  final TextEditingController _controller = TextEditingController();
  bool _isLoading = false;
  String? _answer;
  List<String> _quickInsights = [];

  @override
  void initState() {
    super.initState();
    _loadInsights();
  }

  Future<void> _loadInsights() async {
    final langCode = widget.lang == AppLanguage.tamil ? 'ta' : 'en';
    final list = await widget.apiService.fetchCopilotInsights(lang: langCode);
    if (mounted) {
      setState(() => _quickInsights = list);
    }
  }

  Future<void> _ask(String question) async {
    setState(() {
      _isLoading = true;
      _answer = null;
    });
    final langCode = widget.lang == AppLanguage.tamil ? 'ta' : 'en';
    final res = await widget.apiService.askCopilot(question, lang: langCode);
    if (mounted) {
      setState(() {
        _isLoading = false;
        _answer = res['answer']?.toString() ?? 'Telemetry processed.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isTa = widget.lang == AppLanguage.tamil;

    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.amber.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.smart_toy_rounded, color: Colors.amber, size: 28),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isTa ? 'SEMS AI ஆற்றல் உதவியாளர்' : 'SEMS AI Energy Copilot',
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                      Text(
                        isTa ? 'நேரலை AI ஆலோசனை & கட்டண கணிப்பு' : 'Live Neural Advisory & TNEB Optimization',
                        style: const TextStyle(fontSize: 12, color: Colors.white60),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white70),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Quick Insights Banner
            if (_quickInsights.isNotEmpty) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: Colors.white12),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: _quickInsights.map((ins) => Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2.0),
                    child: Text(
                      ins,
                      style: const TextStyle(fontSize: 12, color: Color(0xFF94A3B8), height: 1.3),
                    ),
                  )).toList(),
                ),
              ),
              const SizedBox(height: 14),
            ],

            // Quick Prompt Chips
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                ActionChip(
                  avatar: const Text('💰'),
                  label: Text(isTa ? 'இன்றைய கட்டணம்?' : "Today's Bill & Slab"),
                  backgroundColor: const Color(0xFF1E293B),
                  labelStyle: const TextStyle(color: Colors.white, fontSize: 11),
                  onPressed: () => _ask(isTa ? 'இன்றைய மின்சார கட்டணம் மற்றும் சேமிப்பு விவரம் என்ன?' : "What is today's estimated bill and active tariff slab?"),
                ),
                ActionChip(
                  avatar: const Text('🚗'),
                  label: Text(isTa ? 'EV சார்ஜ் செய்யலாமா?' : 'Can I charge EV?'),
                  backgroundColor: const Color(0xFF1E293B),
                  labelStyle: const TextStyle(color: Colors.white, fontSize: 11),
                  onPressed: () => _ask(isTa ? 'இப்போது மின்சார வாகனத்தை சார்ஜ் செய்யலாமா?' : 'Can I turn on the EV charger now?'),
                ),
                ActionChip(
                  avatar: const Text('🔋'),
                  label: Text(isTa ? 'பேட்டரி இருப்பு' : 'Battery Backup'),
                  backgroundColor: const Color(0xFF1E293B),
                  labelStyle: const TextStyle(color: Colors.white, fontSize: 11),
                  onPressed: () => _ask(isTa ? 'பேட்டரி எவ்வளவு நேரம் மின் தடைக்கு தாங்கும்?' : 'How long will the battery last during grid outage?'),
                ),
              ],
            ),
            const SizedBox(height: 14),

            // AI Answer Display
            if (_isLoading)
              const Center(child: Padding(padding: EdgeInsets.all(16.0), child: CircularProgressIndicator()))
            else if (_answer != null)
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF0369A1), Color(0xFF0284C7)],
                  ),
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF0284C7).withOpacity(0.3),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          '⚡ SEMS AI ADVISOR',
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: Colors.white70),
                        ),
                        IconButton(
                          icon: const Icon(Icons.volume_up, color: Colors.white, size: 20),
                          tooltip: 'Read Aloud',
                          onPressed: () {
                            // Strip markdown asterisks for clean speech
                            final speech = _answer!.replaceAll('*', '');
                            TtsService().speak(speech, language: widget.lang);
                          },
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      _answer!,
                      style: const TextStyle(fontSize: 13, color: Colors.white, height: 1.4),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 14),

            // Input Row
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    style: const TextStyle(color: Colors.white, fontSize: 13),
                    decoration: InputDecoration(
                      hintText: isTa ? 'கேள்வி கேட்கவும் (எ.கா. AC போடலாமா?)...' : 'Ask Copilot (e.g. Can I run AC?)...',
                      hintStyle: const TextStyle(color: Colors.white38, fontSize: 12),
                      filled: true,
                      fillColor: const Color(0xFF1E293B),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide.none,
                      ),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    ),
                    onSubmitted: (val) {
                      if (val.trim().isNotEmpty) {
                        _ask(val.trim());
                        _controller.clear();
                      }
                    },
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filled(
                  icon: const Icon(Icons.send_rounded),
                  onPressed: () {
                    final val = _controller.text.trim();
                    if (val.isNotEmpty) {
                      _ask(val);
                      _controller.clear();
                    }
                  },
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
