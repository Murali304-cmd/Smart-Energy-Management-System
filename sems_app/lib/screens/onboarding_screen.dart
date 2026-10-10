import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/localization.dart';
import '../providers/user_profile_provider.dart';
import 'home_screen.dart';

class OnboardingScreen extends StatelessWidget {
  const OnboardingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<UserProfileProvider>();
    final lang = profile.language;
    final currentAgeMode = profile.ageMode;

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          // Language Switcher
          Padding(
            padding: const EdgeInsets.only(right: 16.0),
            child: ActionChip(
              avatar: const Icon(Icons.language, size: 18, color: Color(0xFF0284C7)),
              label: Text(
                lang == AppLanguage.tamil ? 'தமிழ் / English' : 'English / தமிழ்',
                style: const TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF0284C7)),
              ),
              backgroundColor: Colors.white,
              side: const BorderSide(color: Color(0xFF0284C7), width: 1.5),
              onPressed: () {
                profile.setLanguage(
                  lang == AppLanguage.tamil ? AppLanguage.english : AppLanguage.tamil,
                );
              },
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 12.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                AppStrings.get('select_age', lang),
                style: const TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.w900,
                  color: Color(0xFF0F172A),
                ),
              ),
              const SizedBox(height: 6),
              Text(
                AppStrings.get('select_age_desc', lang),
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                  color: Color(0xFF64748B),
                ),
              ),
              const SizedBox(height: 28),

              // Option 1: Modern / Youth View
              _buildModeOption(
                context: context,
                isSelected: currentAgeMode == UserAgeMode.young,
                icon: Icons.flash_on_rounded,
                iconColor: const Color(0xFF0284C7),
                title: AppStrings.get('mode_young', lang),
                subtitle: lang == AppLanguage.tamil
                    ? 'நவீன வரைபடங்கள், நேரடி kW அளவீடுகள் மற்றும் தொழில்நுட்ப விபரங்கள்.'
                    : 'Interactive charts, live kW energy flows, and detailed telemetry.',
                tag: 'Tech & Graphs',
                onTap: () => profile.setAgeMode(UserAgeMode.young),
              ),

              const SizedBox(height: 18),

              // Option 2: Simple / Senior (Elder) View
              _buildModeOption(
                context: context,
                isSelected: currentAgeMode == UserAgeMode.elder,
                icon: Icons.accessibility_new_rounded,
                iconColor: const Color(0xFFD97706),
                title: AppStrings.get('mode_elder', lang),
                subtitle: lang == AppLanguage.tamil
                    ? 'பெரிய எழுத்துக்கள், எளிய சொற்கள், பேசும் குரல் உதவி மற்றும் உடனடி பில் கணக்கு.'
                    : 'Large high-contrast text, clear simple terms, and voice readout for 1-day units & bill.',
                tag: 'Large Text & Voice',
                onTap: () => profile.setAgeMode(UserAgeMode.elder),
              ),

              const Spacer(),

              // Continue Button
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF0284C7),
                  foregroundColor: Colors.white,
                  minimumSize: const Size(double.infinity, 60),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  elevation: 2,
                ),
                onPressed: () async {
                  await profile.completeOnboarding();
                  if (!context.mounted) return;
                  Navigator.pushReplacement(
                    context,
                    MaterialPageRoute(builder: (_) => const HomeScreen()),
                  );
                },
                child: Text(
                  AppStrings.get('continue_btn', lang),
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(height: 12),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildModeOption({
    required BuildContext context,
    required bool isSelected,
    required IconData icon,
    required Color iconColor,
    required String title,
    required String subtitle,
    required String tag,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected ? const Color(0xFF0284C7) : const Color(0xFFCBD5E1),
            width: isSelected ? 3.0 : 1.5,
          ),
          boxShadow: [
            BoxShadow(
              color: isSelected ? const Color(0xFF0284C7).withOpacity(0.12) : Colors.black.withOpacity(0.04),
              blurRadius: 10,
              offset: const Offset(0, 4),
            )
          ],
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: iconColor.withOpacity(0.15),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: iconColor, size: 32),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text(
                          title,
                          style: const TextStyle(
                            fontSize: 19,
                            fontWeight: FontWeight.w900,
                            color: Color(0xFF0F172A),
                          ),
                        ),
                      ),
                      if (isSelected)
                        const Icon(Icons.check_circle_rounded, color: Color(0xFF0284C7), size: 26),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF1F5F9),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      tag,
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF475569),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    subtitle,
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: Color(0xFF475569),
                      height: 1.3,
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
}
