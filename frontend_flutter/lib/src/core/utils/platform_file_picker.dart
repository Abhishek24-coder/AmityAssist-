import 'dart:async';
import 'package:flutter/foundation.dart';
import 'platform_file_picker_models.dart';
import 'platform_file_picker_interop.dart';
import 'platform_file_picker_desktop_interop.dart';

export 'platform_file_picker_models.dart';

/// Cross-platform document file picker supporting Web, Windows Desktop, and mobile.
class PlatformFilePicker {
  /// Opens a native system file picker dialog to pick document files.
  /// Returns null if the user cancels or dismisses the picker dialog.
  static Future<PickedDocFile?> pickDocument({String accept = '.pdf,.jpg,.jpeg,.png'}) async {
    if (kIsWeb) {
      return WebFilePickerBridge.pickFile(accept: accept);
    }
    return DesktopFilePicker.pickDocument(accept: accept);
  }
}
