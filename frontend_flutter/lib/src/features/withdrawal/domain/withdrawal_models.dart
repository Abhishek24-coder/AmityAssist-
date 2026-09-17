class WithdrawalGuide {
  const WithdrawalGuide({
    required this.title,
    required this.summary,
    required this.principle,
    required this.steps,
    required this.documents,
    required this.forms,
    required this.officialTimeline,
  });

  factory WithdrawalGuide.fromJson(Map<String, dynamic> json) {
    return WithdrawalGuide(
      title: json['title'] as String? ?? 'Withdrawal Intelligence System',
      summary: json['summary'] as String? ?? '',
      principle: json['principle'] as String? ?? '',
      steps: (json['steps'] as List? ?? [])
          .map((item) => WithdrawalStep.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
      documents: (json['documents'] as List? ?? [])
          .map((item) => WithdrawalDocument.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
      forms: (json['forms'] as List? ?? [])
          .map((item) => WithdrawalForm.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
      officialTimeline: (json['official_timeline'] as List? ?? [])
          .map((item) => TimelineBand.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
    );
  }

  final String title;
  final String summary;
  final String principle;
  final List<WithdrawalStep> steps;
  final List<WithdrawalDocument> documents;
  final List<WithdrawalForm> forms;
  final List<TimelineBand> officialTimeline;
}

class WithdrawalStep {
  const WithdrawalStep({
    required this.stepNumber,
    required this.title,
    required this.description,
    required this.department,
    required this.timelineText,
  });

  factory WithdrawalStep.fromJson(Map<String, dynamic> json) {
    return WithdrawalStep(
      stepNumber: json['step_number'] as int? ?? 0,
      title: json['title'] as String? ?? '',
      description: json['description'] as String? ?? '',
      department: json['department'] as String? ?? '',
      timelineText: json['timeline_text'] as String? ?? '',
    );
  }

  final int stepNumber;
  final String title;
  final String description;
  final String department;
  final String timelineText;
}

class WithdrawalDocument {
  const WithdrawalDocument({
    required this.name,
    required this.description,
    required this.mandatory,
  });

  factory WithdrawalDocument.fromJson(Map<String, dynamic> json) {
    return WithdrawalDocument(
      name: json['name'] as String? ?? '',
      description: json['description'] as String? ?? '',
      mandatory: json['mandatory'] as bool? ?? false,
    );
  }

  final String name;
  final String description;
  final bool mandatory;
}

class WithdrawalForm {
  const WithdrawalForm({
    required this.name,
    required this.description,
    required this.downloadUrl,
    required this.issuingDepartment,
  });

  factory WithdrawalForm.fromJson(Map<String, dynamic> json) {
    return WithdrawalForm(
      name: json['name'] as String? ?? '',
      description: json['description'] as String? ?? '',
      downloadUrl: json['download_url'] as String? ?? '',
      issuingDepartment: json['issuing_department'] as String? ?? '',
    );
  }

  final String name;
  final String description;
  final String downloadUrl;
  final String issuingDepartment;

  String get fullDownloadUrl {
    if (downloadUrl.startsWith('http')) {
      return downloadUrl;
    }
    return 'http://127.0.0.1:8000$downloadUrl';
  }
}

class TimelineBand {
  const TimelineBand({required this.stage, required this.timeline});

  factory TimelineBand.fromJson(Map<String, dynamic> json) {
    return TimelineBand(
      stage: json['stage'] as String? ?? '',
      timeline: json['timeline'] as String? ?? '',
    );
  }

  final String stage;
  final String timeline;
}

class ClearanceGateItem {
  const ClearanceGateItem({
    required this.department,
    required this.sequenceOrder,
    required this.status,
    this.officerName,
    this.officerId,
    this.clearedAt,
    this.notes,
    this.duesAmount = 0.0,
  });

  factory ClearanceGateItem.fromJson(Map<String, dynamic> json) {
    return ClearanceGateItem(
      department: json['department'] as String? ?? '',
      sequenceOrder: json['sequence_order'] as int? ?? 1,
      status: json['status'] as String? ?? 'PENDING',
      officerName: json['officer_name'] as String?,
      officerId: json['officer_id'] as String?,
      clearedAt: json['cleared_at'] as String?,
      notes: json['notes'] as String?,
      duesAmount: (json['dues_amount'] as num?)?.toDouble() ?? 0.0,
    );
  }

  final String department;
  final int sequenceOrder;
  final String status;
  final String? officerName;
  final String? officerId;
  final String? clearedAt;
  final String? notes;
  final double duesAmount;
}

class ClearanceVoucher {
  const ClearanceVoucher({
    required this.referenceNo,
    required this.studentId,
    required this.studentName,
    required this.course,
    required this.semester,
    required this.submissionDate,
    required this.currentStatus,
    required this.ordinanceClause,
    required this.grossFeePaid,
    required this.refundPercentage,
    required this.deductions,
    required this.netRefundableAmount,
    required this.cautionDepositBalance,
    required this.gates,
  });

  factory ClearanceVoucher.fromJson(Map<String, dynamic> json) {
    return ClearanceVoucher(
      referenceNo: json['reference_no'] as String? ?? '',
      studentId: json['student_id'] as String? ?? '',
      studentName: json['student_name'] as String? ?? 'Student',
      course: json['course'] as String? ?? 'Undergraduate Program',
      semester: json['semester'] as int? ?? 1,
      submissionDate: json['submission_date'] as String? ?? '',
      currentStatus: json['current_status'] as String? ?? 'pending',
      ordinanceClause: json['ordinance_clause'] as String? ?? '',
      grossFeePaid: (json['gross_fee_paid'] as num?)?.toDouble() ?? 0.0,
      refundPercentage: (json['refund_percentage'] as num?)?.toDouble() ?? 0.0,
      deductions: (json['deductions'] as num?)?.toDouble() ?? 0.0,
      netRefundableAmount: (json['net_refundable_amount'] as num?)?.toDouble() ?? 0.0,
      cautionDepositBalance: (json['caution_deposit_balance'] as num?)?.toDouble() ?? 0.0,
      gates: (json['gates'] as List? ?? [])
          .map((g) => ClearanceGateItem.fromJson(Map<String, dynamic>.from(g as Map)))
          .toList(),
    );
  }

  final String referenceNo;
  final String studentId;
  final String studentName;
  final String course;
  final int semester;
  final String submissionDate;
  final String currentStatus;
  final String ordinanceClause;
  final double grossFeePaid;
  final double refundPercentage;
  final double deductions;
  final double netRefundableAmount;
  final double cautionDepositBalance;
  final List<ClearanceGateItem> gates;
}
