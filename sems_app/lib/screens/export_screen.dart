import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';
import '../core/localization.dart';
import '../providers/user_profile_provider.dart';
import '../providers/energy_provider.dart';

class ExportScreen extends StatelessWidget {
  const ExportScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<UserProfileProvider>();
    final energy = context.watch<EnergyProvider>();
    final isElder = profile.isElder;
    final lang = profile.language;
    final usage = energy.usage;
    final now = DateTime.now();

    final dateStr = '${now.day}/${now.month}/${now.year}';
    final shareText = '''
⚡ Smart Energy Management System (SEMS) Daily Report
📅 Date: $dateStr
📊 Units Used Today: ${usage.totalUnitsToday.toStringAsFixed(2)} Units (kWh)
☀️ Solar Generated: ${usage.solarUnitsToday.toStringAsFixed(2)} Units
🔋 Battery Discharged: ${usage.batteryUnitsDischargedToday.toStringAsFixed(2)} Units
🔌 EB Grid Imported: ${usage.gridUnitsImportedToday.toStringAsFixed(2)} Units
💰 1-Day Total Bill: ₹ ${usage.totalAmountToday.toStringAsFixed(2)}
🌿 Money Saved Today: ₹ ${usage.moneySavedToday.toStringAsFixed(2)}
🏷️ TNEB Slab: ${usage.currentSlabName}
''';

    return Scaffold(
      appBar: AppBar(
        title: Text(
          AppStrings.get('share_report', lang),
          style: TextStyle(
            fontSize: isElder ? 20 : 18,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Bill Preview Card
            Container(
              padding: EdgeInsets.all(isElder ? 22 : 16),
              decoration: BoxDecoration(
                color: isElder ? Colors.white : Theme.of(context).cardTheme.color,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(
                  color: isElder ? const Color(0xFF64748B) : Colors.white12,
                  width: isElder ? 2.0 : 1.0,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'SEMS DAILY BILL RECEIPT',
                        style: TextStyle(
                          fontSize: isElder ? 17 : 14,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 1,
                          color: const Color(0xFF0284C7),
                        ),
                      ),
                      Text(
                        dateStr,
                        style: TextStyle(
                          fontSize: isElder ? 15 : 12,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  const Divider(height: 24),
                  _buildReceiptRow('Units Used Today (Gross)', '${usage.totalUnitsToday.toStringAsFixed(2)} Units', isElder),
                  _buildReceiptRow('Solar Power Generated', '- ${usage.solarUnitsToday.toStringAsFixed(2)} Units', isElder, isGreen: true),
                  _buildReceiptRow('Battery Supplied Units', '- ${usage.batteryUnitsDischargedToday.toStringAsFixed(2)} Units', isElder, isGreen: true),
                  _buildReceiptRow('Net Grid Units Billed', '${usage.gridUnitsImportedToday.toStringAsFixed(2)} Units', isElder),
                  _buildReceiptRow('Active TNEB Slab', usage.currentSlabName, isElder),
                  const Divider(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Total 1-Day Bill Amount',
                        style: TextStyle(
                          fontSize: isElder ? 19 : 16,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      Text(
                        '₹ ${usage.totalAmountToday.toStringAsFixed(2)}',
                        style: TextStyle(
                          fontSize: isElder ? 26 : 22,
                          fontWeight: FontWeight.w900,
                          color: isElder ? Colors.black : const Color(0xFF38BDF8),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Net Savings Today: ₹ ${usage.moneySavedToday.toStringAsFixed(2)}',
                    style: TextStyle(
                      fontSize: isElder ? 16 : 13,
                      fontWeight: FontWeight.bold,
                      color: Colors.green,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Share via WhatsApp / SMS Button
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF25D366), // WhatsApp Green
                foregroundColor: Colors.white,
                minimumSize: Size(double.infinity, isElder ? 64 : 54),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              ),
              icon: const Icon(Icons.share_rounded, size: 24),
              label: Text(
                isElder ? 'பில் விவரத்தை பகிர்க (WhatsApp / SMS)' : 'Share Summary via WhatsApp / SMS',
                style: TextStyle(fontSize: isElder ? 17 : 15, fontWeight: FontWeight.bold),
              ),
              onPressed: () {
                Share.share(shareText, subject: 'Daily Energy Consumption Report');
              },
            ),
            const SizedBox(height: 12),

            // Download PDF Receipt
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFF0284C7),
                side: const BorderSide(color: Color(0xFF0284C7), width: 2),
                minimumSize: Size(double.infinity, isElder ? 64 : 54),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              ),
              icon: const Icon(Icons.picture_as_pdf_rounded, size: 24),
              label: Text(
                isElder ? 'பில் PDF பதிவிறக்கம்' : 'Download / Print PDF Receipt',
                style: TextStyle(fontSize: isElder ? 17 : 15, fontWeight: FontWeight.bold),
              ),
              onPressed: () async {
                await _generateAndPrintPdf(usage, dateStr);
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildReceiptRow(String title, String value, bool isElder, {bool isGreen = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Text(
              title,
              style: TextStyle(
                fontSize: isElder ? 15 : 13,
                color: isElder ? const Color(0xFF334155) : Colors.grey,
              ),
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: isElder ? 16 : 14,
              fontWeight: FontWeight.bold,
              color: isGreen ? Colors.green : (isElder ? Colors.black : null),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _generateAndPrintPdf(dynamic usage, String dateStr) async {
    final pdf = pw.Document();

    pdf.addPage(
      pw.Page(
        pageFormat: PdfPageFormat.a4,
        build: (pw.Context context) {
          return pw.Padding(
            padding: const pw.EdgeInsets.all(24),
            child: pw.Column(
              crossAxisAlignment: pw.CrossAxisAlignment.start,
              children: [
                pw.Header(
                  level: 0,
                  child: pw.Text('Smart Energy Management System - Daily Bill', style: pw.TextStyle(fontSize: 22, fontWeight: pw.FontWeight.bold)),
                ),
                pw.Text('Date: $dateStr'),
                pw.SizedBox(height: 16),
                pw.TableHelper.fromTextArray(
                  context: context,
                  data: [
                    ['Metric', 'Value'],
                    ['Units Used Today (kWh)', '${usage.totalUnitsToday.toStringAsFixed(2)} Units'],
                    ['Solar Power Generated', '${usage.solarUnitsToday.toStringAsFixed(2)} Units'],
                    ['Battery Storage Supplied', '${usage.batteryUnitsDischargedToday.toStringAsFixed(2)} Units'],
                    ['Net Grid Imported (EB)', '${usage.gridUnitsImportedToday.toStringAsFixed(2)} Units'],
                    ['TNEB Slab Applied', '${usage.currentSlabName}'],
                    ['Total 1-Day Bill Amount', 'Rs. ${usage.totalAmountToday.toStringAsFixed(2)}'],
                    ['Money Saved with Solar', 'Rs. ${usage.moneySavedToday.toStringAsFixed(2)}'],
                  ],
                ),
                pw.SizedBox(height: 20),
                pw.Text('Generated by SEMS AI Microgrid Platform (FastAPI + Flutter)'),
              ],
            ),
          );
        },
      ),
    );

    await Printing.layoutPdf(
      onLayout: (PdfPageFormat format) async => pdf.save(),
    );
  }
}
