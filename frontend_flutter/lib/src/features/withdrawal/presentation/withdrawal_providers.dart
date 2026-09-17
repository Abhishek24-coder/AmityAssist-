import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api_client.dart';
import '../data/withdrawal_repository.dart';
import '../domain/withdrawal_models.dart';

final withdrawalRepositoryProvider = Provider<WithdrawalRepository>(
  (ref) => WithdrawalRepository(ref.watch(apiClientProvider)),
);

final withdrawalGuideProvider = FutureProvider<WithdrawalGuide>((ref) {
  return ref.watch(withdrawalRepositoryProvider).fetchGuide();
});

final clearanceVoucherProvider = FutureProvider.family<ClearanceVoucher, String>((ref, referenceNo) {
  return ref.watch(withdrawalRepositoryProvider).fetchClearanceVoucher(referenceNo);
});
