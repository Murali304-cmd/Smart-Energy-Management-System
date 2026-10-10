import 'package:flutter_tts/flutter_tts.dart';
import '../core/localization.dart';

class TtsService {
  static final TtsService _instance = TtsService._internal();
  factory TtsService() => _instance;
  TtsService._internal();

  final FlutterTts _flutterTts = FlutterTts();
  bool _isPlaying = false;
  bool get isPlaying => _isPlaying;

  Future<void> init() async {
    try {
      await _flutterTts.setSpeechRate(0.45); // Slower, clear voice for elderly
      await _flutterTts.setVolume(1.0);
      await _flutterTts.setPitch(1.0);

      _flutterTts.setCompletionHandler(() {
        _isPlaying = false;
      });
      _flutterTts.setErrorHandler((_) {
        _isPlaying = false;
      });
    } catch (_) {}
  }

  /// Speak current energy summary in selected language
  Future<void> speakSummary({
    required double totalUnits,
    required double cost,
    required double solarUnits,
    required double backupHours,
    required AppLanguage language,
  }) async {
    try {
      if (_isPlaying) {
        await stop();
        return;
      }

      String message;
      if (language == AppLanguage.tamil) {
        await _flutterTts.setLanguage('ta-IN');
        message = 'வணக்கம். இன்று நீங்கள் பயன்படுத்திய மின்சாரம் ${totalUnits.toStringAsFixed(1)} யூனிட்டுகள் ஆகும். '
            'இன்றைய உத்தேச கட்டணம் ${cost.toStringAsFixed(0)} ரூபாய். '
            'சூரிய மின்சாரத்தால் ${solarUnits.toStringAsFixed(1)} யூனிட் மிச்சமாகியுள்ளது. '
            'உங்கள் வீட்டு பேட்டரி இன்னும் ${backupHours.toStringAsFixed(0)} மணி நேரம் மின்சாரம் தரும்.';
      } else {
        await _flutterTts.setLanguage('en-IN');
        message = 'Hello. Total electricity used today is ${totalUnits.toStringAsFixed(1)} units. '
            'The total estimated bill is ${cost.toStringAsFixed(2)} rupees. '
            'You generated ${solarUnits.toStringAsFixed(1)} units from solar energy. '
            'Your battery will supply power for approximately ${backupHours.toStringAsFixed(1)} hours.';
      }

      _isPlaying = true;
      await _flutterTts.speak(message);
    } catch (_) {
      _isPlaying = false;
    }
  }

  Future<void> stop() async {
    try {
      await _flutterTts.stop();
      _isPlaying = false;
    } catch (_) {}
  }
}
