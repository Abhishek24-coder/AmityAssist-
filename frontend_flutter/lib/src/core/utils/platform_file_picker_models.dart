import 'dart:typed_data';

class PickedDocFile {
  final String name;
  final int size;
  final String? path;
  final Uint8List? bytes;

  const PickedDocFile({
    required this.name,
    required this.size,
    this.path,
    this.bytes,
  });

  String get formattedSize {
    if (size < 1024) return '$size B';
    if (size < 1024 * 1024) return '${(size / 1024).toStringAsFixed(1)} KB';
    return '${(size / (1024 * 1024)).toStringAsFixed(1)} MB';
  }
}
