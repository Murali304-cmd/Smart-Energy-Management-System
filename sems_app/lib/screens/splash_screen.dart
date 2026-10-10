import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/user_profile_provider.dart';
import '../providers/energy_provider.dart';
import 'onboarding_screen.dart';
import 'home_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _navigateNext();
  }

  void _navigateNext() async {
    await Future.delayed(const Duration(milliseconds: 1800));
    if (!mounted) return;

    final profile = context.read<UserProfileProvider>();
    final energy = context.read<EnergyProvider>();
    energy.setupHourlyNotifications(profile);

    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (_) => const HomeScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(22),
              decoration: BoxDecoration(
                color: const Color(0xFF0284C7).withOpacity(0.2),
                shape: BoxShape.circle,
                border: Border.all(color: const Color(0xFF0284C7), width: 2),
              ),
              child: const Icon(
                Icons.bolt_rounded,
                size: 72,
                color: Color(0xFF38BDF8),
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'SEMS',
              style: TextStyle(
                fontSize: 36,
                fontWeight: FontWeight.w900,
                color: Colors.white,
                letterSpacing: 2,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Smart Energy Management System',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w500,
                color: Color(0xFF94A3B8),
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'ஸ்மார்ட் மின்சார மேலாண்மை அமைப்பு',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: Color(0xFF38BDF8),
              ),
            ),
            const SizedBox(height: 36),
            const SizedBox(
              width: 36,
              height: 36,
              child: CircularProgressIndicator(
                strokeWidth: 3,
                valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF38BDF8)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
