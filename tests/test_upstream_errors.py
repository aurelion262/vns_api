"""Classifier tests — upstream_errors.is_upstream_quota_error (plan R2 §4.1).

Exhaustion grammar only: mọi positive là tín hiệu cạn/vượt hạn mức; negatives gồm
CHÍNH các marker nhưng mang nghĩa cấu hình/parse/argument (verdict R1 F1) —
tất cả phải trả False (giữ 500 default). KHÔNG test typed object (dead branch đã
bỏ theo verdict R1 F2 — detail production luôn là str).
"""
from upstream_errors import is_upstream_quota_error

# (label, detail, expected)
CASES = [
    # --- Positives: mỗi pattern ≥1 (plan R2 §3.3, thứ tự tương ứng) ---
    ("p1 canonical vendor", "Rate limit exceeded for provider 'vci'", True),
    ("p2 quota exceeded", "You have quota exceeded for today", True),
    ("p3 out of quota", "Account is out of quota", True),
    ("p4 hết lượt", "Bạn đã hết lượt truy vấn hôm nay", True),
    ("p5 vượt quá lượt", "vượt quá lượt cho phép", True),
    ("p5b vượt quá số lượt", "Tài khoản vượt quá số lượt yêu cầu", True),
    ("p6 vượt quá giới hạn", "Yêu cầu vượt quá giới hạn cho phép", True),
    # --- Negatives: marker có mặt nhưng NON-exhaustion (verdict R1 F1) ---
    ("n1 quota config missing", "quota configuration missing", False),
    ("n2 invalid rate limit argument", "invalid rate limit argument", False),
    ("n3 cannot parse quota field", "cannot parse quota field", False),
    ("n4 thiếu cấu hình quota", "thiếu cấu hình quota", False),
    ("n5 đối số rate limit không hợp lệ", "đối số rate limit không hợp lệ", False),
    # --- Negatives thường ---
    ("n6 lỗi logic", "boom", False),
    ("n7 không tìm thấy", "Không tìm thấy dữ liệu", False),
    ("n8 KBS không hỗ trợ", "KBS không cung cấp ICB classification", False),
    # --- Edge: không string / rỗng (không suy diễn) ---
    ("e1 None", None, False),
    ("e2 empty", "", False),
    ("e3 non-string", ValueError("quota exceeded"), False),
]


def test_classifier_table():
    for label, detail, expected in CASES:
        got = is_upstream_quota_error(detail)
        assert got is expected, f"{label}: expected {expected}, got {got}"
