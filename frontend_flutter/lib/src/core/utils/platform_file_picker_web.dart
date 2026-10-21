import 'dart:async';
import 'dart:js_interop';
import 'dart:js_interop_unsafe';
import 'dart:typed_data';
import 'platform_file_picker_models.dart';

class WebFilePickerBridge {
  static Future<PickedDocFile?> pickFile({String accept = '.pdf,.jpg,.jpeg,.png,.docx'}) async {
    final completer = Completer<PickedDocFile?>();
    try {
      final picker = globalContext['uniassistFilePicker'] as JSObject?;
      if (picker == null) {
        completer.complete(null);
      } else {
        final fn = picker['pickFile'] as JSFunction?;
        if (fn == null) {
          completer.complete(null);
        } else {
          final callbackJS = ((JSAny? fileObj) {
            if (fileObj == null) {
              if (!completer.isCompleted) completer.complete(null);
              return;
            }
            try {
              final jsMap = fileObj as JSObject;
              final nameStr = (jsMap['name'] as JSString?)?.toDart ?? 'document.pdf';
              final sizeNum = (jsMap['size'] as JSNumber?)?.toDartInt ?? 0;
              final jsBytes = jsMap['bytes'] as JSUint8Array?;
              Uint8List? bytes;
              if (jsBytes != null) {
                bytes = jsBytes.toDart;
              }

              if (!completer.isCompleted) {
                completer.complete(PickedDocFile(
                  name: nameStr,
                  size: sizeNum,
                  bytes: bytes,
                ));
              }
            } catch (e) {
              if (!completer.isCompleted) completer.complete(null);
            }
          }).toJS;

          fn.callAsFunction(picker, accept.toJS, callbackJS);
        }
      }
    } catch (_) {
      if (!completer.isCompleted) completer.complete(null);
    }
    return await completer.future;
  }
}
