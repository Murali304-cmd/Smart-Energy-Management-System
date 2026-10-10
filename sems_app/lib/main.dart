import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/theme.dart';
import 'core/notification_service.dart';
import 'services/tts_service.dart';
import 'providers/user_profile_provider.dart';
import 'providers/energy_provider.dart';
import 'screens/splash_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize notification and voice services
  await NotificationService().initialize();
  await TtsService().init();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => UserProfileProvider()),
        ChangeNotifierProvider(create: (_) => EnergyProvider()),
      ],
      child: const SemsApp(),
    ),
  );
}

class SemsApp extends StatelessWidget {
  const SemsApp({super.key});

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<UserProfileProvider>();

    return MaterialApp(
      title: 'Smart Energy Management System',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.getTheme(
        isDark: profile.isDarkMode,
        ageMode: profile.ageMode,
      ),
      home: const SplashScreen(),
    );
  }
}
