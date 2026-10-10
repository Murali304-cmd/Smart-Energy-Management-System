import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/localization.dart';
import '../providers/user_profile_provider.dart';
import '../providers/energy_provider.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late TextEditingController _urlController;

  @override
  void initState() {
    super.initState();
    final energy = context.read<EnergyProvider>();
    _urlController = TextEditingController(text: energy.serverBaseUrl);
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<UserProfileProvider>();
    final energy = context.watch<EnergyProvider>();
    final isElder = profile.isElder;
    final lang = profile.language;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 12.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Language Selector
          Container(
            padding: EdgeInsets.all(isElder ? 18 : 14),
            decoration: BoxDecoration(
              color: isElder ? Colors.white : Theme.of(context).cardTheme.color,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: isElder ? const Color(0xFF64748B) : Colors.white10,
                width: isElder ? 2.0 : 1.0,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isElder ? 'மொழி (Language)' : 'App Language',
                  style: TextStyle(
                    fontSize: isElder ? 18 : 15,
                    fontWeight: FontWeight.bold,
                    color: isElder ? Colors.black : null,
                  ),
                ),
                const SizedBox(height: 10),
                SegmentedButton<AppLanguage>(
                  segments: const [
                    ButtonSegment(
                      value: AppLanguage.english,
                      label: Text('English'),
                    ),
                    ButtonSegment(
                      value: AppLanguage.tamil,
                      label: Text('தமிழ் (Tamil)'),
                    ),
                  ],
                  selected: {profile.language},
                  onSelectionChanged: (newSelection) {
                    profile.setLanguage(newSelection.first);
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // Hourly Notifications Toggle
          Container(
            padding: EdgeInsets.all(isElder ? 18 : 14),
            decoration: BoxDecoration(
              color: isElder ? Colors.white : Theme.of(context).cardTheme.color,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: isElder ? const Color(0xFF64748B) : Colors.white10,
                width: isElder ? 2.0 : 1.0,
              ),
            ),
            child: SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(
                isElder ? 'ஒவ்வொரு மணி நேரமும் அறிவிப்பு' : 'Hourly Energy Reports (FCM / Local)',
                style: TextStyle(
                  fontSize: isElder ? 17 : 14,
                  fontWeight: FontWeight.bold,
                  color: isElder ? Colors.black : null,
                ),
              ),
              subtitle: Text(
                isElder
                    ? 'ஒவ்வொரு மணி நேரமும் எத்தனை யூனிட் செலவானது என்று போனில் செய்தி வரும்.'
                    : 'Fires hourly notification with units consumed, total day units, and bill so far.',
                style: TextStyle(
                  fontSize: isElder ? 14 : 12,
                  color: isElder ? const Color(0xFF334155) : Colors.grey,
                ),
              ),
              value: profile.hourlyNotificationsEnabled,
              onChanged: (val) {
                profile.setHourlyNotifications(val);
                energy.setupHourlyNotifications(profile);
              },
            ),
          ),
          const SizedBox(height: 14),

          // Server Connection URL
          Container(
            padding: EdgeInsets.all(isElder ? 18 : 14),
            decoration: BoxDecoration(
              color: isElder ? Colors.white : Theme.of(context).cardTheme.color,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: isElder ? const Color(0xFF64748B) : Colors.white10,
                width: isElder ? 2.0 : 1.0,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'FastAPI Backend Server URL',
                  style: TextStyle(
                    fontSize: isElder ? 17 : 14,
                    fontWeight: FontWeight.bold,
                    color: isElder ? Colors.black : null,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'Default: http://10.0.2.2:8080 (Emulator) or http://192.168.x.x:8080 (Phone)',
                  style: TextStyle(fontSize: isElder ? 13 : 11, color: Colors.grey),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _urlController,
                        decoration: InputDecoration(
                          hintText: 'http://10.0.2.2:8080',
                          filled: true,
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF0284C7),
                        foregroundColor: Colors.white,
                      ),
                      onPressed: () {
                        energy.setBaseUrl(_urlController.text);
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Server URL updated! Refreshing...')),
                        );
                      },
                      child: const Text('Save'),
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
