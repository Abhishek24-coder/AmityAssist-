import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api_client.dart';
import '../../../core/theme/kiosk_theme.dart';
import '../../auth/application/auth_provider.dart';

class WithdrawalFlowScreen extends ConsumerStatefulWidget {
  const WithdrawalFlowScreen({super.key});

  @override
  ConsumerState<WithdrawalFlowScreen> createState() => _WithdrawalFlowScreenState();
}

class _WithdrawalFlowScreenState extends ConsumerState<WithdrawalFlowScreen> {
  int _currentStep = 0;
  String? _reason;
  bool _isSubmitting = false;

  final _reasons = [
    'Medical Reasons',
    'Financial Hardship',
    'Transferring to another university',
    'Personal Reasons',
    'Other'
  ];

  Future<void> _submitRequest() async {
    setState(() => _isSubmitting = true);
    final auth = ref.read(authProvider);
    final studentId = auth.studentId ?? 'STU001';

    try {
      final dio = ref.read(apiClientProvider);

      // Submit official withdrawal initiating 4 clearance gates & caution deposit ledger
      final response = await dio.post('/withdrawal/apply', data: {
        'student_id': studentId,
        'reason': _reason,
        'intent': 'withdrawal_official',
      });

      final data = response.data as Map<String, dynamic>;
      final refNo = data['reference_no']?.toString() ?? 'AMITY-WTH-2026';
      final voucher = data['voucher'] as Map<String, dynamic>?;
      final refundAmt = voucher?['net_refundable_amount']?.toString() ?? '119,000.00';

      if (mounted) {
        showDialog(
          context: context,
          barrierDismissible: false,
          builder: (dialogCtx) => AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            title: const Row(
              children: [
                Icon(Icons.check_circle_rounded, color: AppColors.successGreen, size: 28),
                SizedBox(width: 10),
                Text('Withdrawal Submitted', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              ],
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Your clearance chain has been initialized across 4 university gates.'),
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppColors.primary.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppColors.primary.withValues(alpha: 0.2)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Official Reference Token:', style: TextStyle(fontSize: 12, color: Colors.grey, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 4),
                      SelectableText(
                        refNo,
                        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: AppColors.primary),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        'Estimated Net Refund: ₹$refundAmt',
                        style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppColors.successGreen),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                const Text(
                  'Track this application anytime using your token at the kiosk or under Live Clearance Tracker.',
                  style: TextStyle(fontSize: 12, color: Colors.grey),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () {
                  Navigator.pop(dialogCtx);
                  Navigator.pop(context);
                },
                child: const Text('Return to Home'),
              ),
              FilledButton.icon(
                onPressed: () {
                  Navigator.pop(dialogCtx);
                  Navigator.pop(context);
                  context.push('/request-status');
                },
                icon: const Icon(Icons.track_changes_rounded, size: 18),
                label: const Text('Track 4-Gate Status'),
              ),
            ],
          ),
        );
      }
    } on DioException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${e.response?.data?['detail'] ?? e.message}')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error submitting request: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Initiate Withdrawal')),
      body: Stepper(
        type: StepperType.vertical,
        currentStep: _currentStep,
        onStepContinue: () {
          if (_currentStep == 0 && _reason == null) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Please select a reason.')),
            );
            return;
          }
          if (_currentStep < 2) {
            setState(() => _currentStep += 1);
          } else {
            _submitRequest();
          }
        },
        onStepCancel: () {
          if (_currentStep > 0) {
            setState(() => _currentStep -= 1);
          } else {
            Navigator.pop(context);
          }
        },
        controlsBuilder: (context, details) {
          final isLastStep = _currentStep == 2;
          return Padding(
            padding: const EdgeInsets.only(top: 24),
            child: Row(
              children: [
                FilledButton(
                  onPressed: _isSubmitting ? null : details.onStepContinue,
                  child: _isSubmitting
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white),
                        )
                      : Text(isLastStep ? 'Submit Request' : 'Continue'),
                ),
                const SizedBox(width: 12),
                if (!isLastStep)
                  OutlinedButton(
                    onPressed: details.onStepCancel,
                    child: const Text('Cancel'),
                  ),
              ],
            ),
          );
        },
        steps: [
          Step(
            title: const Text('Select Reason'),
            content: DropdownButtonFormField<String>(
              initialValue: _reason,
              decoration:
                  const InputDecoration(labelText: 'Reason for Withdrawal'),
              items: _reasons
                  .map((r) => DropdownMenuItem(value: r, child: Text(r)))
                  .toList(),
              onChanged: (v) => setState(() => _reason = v),
            ),
            isActive: _currentStep >= 0,
            state:
                _currentStep > 0 ? StepState.complete : StepState.indexed,
          ),
          Step(
            title: const Text('Required Documents'),
            content: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                    'Based on your reason, the following documents are required:'),
                SizedBox(height: 12),
                ListTile(
                  leading: Icon(Icons.description),
                  title: Text('Withdrawal Application Form'),
                  subtitle: Text('Please download, sign, and upload.'),
                ),
                ListTile(
                  leading: Icon(Icons.receipt),
                  title: Text('Fee Clearance Form'),
                  subtitle: Text('Clearance from Finance Dept.'),
                ),
                ListTile(
                  leading: Icon(Icons.library_books),
                  title: Text('Library No-Dues Certificate'),
                  subtitle: Text('Clearance from Central Library.'),
                ),
              ],
            ),
            isActive: _currentStep >= 1,
            state:
                _currentStep > 1 ? StepState.complete : StepState.indexed,
          ),
          Step(
            title: const Text('Upload & Submit'),
            content: Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                border: Border.all(
                    color: Colors.grey.shade400, style: BorderStyle.solid),
                borderRadius: BorderRadius.circular(12),
                color: Colors.grey.shade100,
              ),
              child: const Center(
                child: Column(
                  children: [
                    Icon(Icons.upload_file, size: 48, color: Colors.grey),
                    SizedBox(height: 12),
                    Text('Tap to scan or upload your signed documents'),
                  ],
                ),
              ),
            ),
            isActive: _currentStep >= 2,
          ),
        ],
      ),
    );
  }
}
