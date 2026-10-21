import 'dart:io';
import 'platform_file_picker_models.dart';

class DesktopFilePicker {
  static Future<PickedDocFile?> pickDocument({String accept = '.pdf,.jpg,.jpeg,.png,.docx'}) async {
    if (Platform.isWindows) {
      try {
        const psScript = '''
[System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms") | Out-Null
\$dialog = New-Object System.Windows.Forms.OpenFileDialog
\$dialog.Filter = "Documents (*.pdf;*.jpg;*.png;*.docx)|*.pdf;*.jpg;*.png;*.docx|All Files (*.*)|*.*"
\$dialog.Title = "Select Verification Document"
if (\$dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
  Write-Output \$dialog.FileName
}
''';
        final result = await Process.run(
          'powershell',
          ['-NoProfile', '-STA', '-Command', psScript],
          runInShell: true,
        );

        final out = result.stdout.toString().trim();
        if (out.isNotEmpty && File(out).existsSync()) {
          final file = File(out);
          final bytes = await file.readAsBytes();
          final name = file.uri.pathSegments.last;
          return PickedDocFile(
            name: name,
            size: bytes.length,
            path: out,
            bytes: bytes,
          );
        }
      } catch (_) {}
    }
    return null;
  }
}
