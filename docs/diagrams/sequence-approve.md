# Sơ đồ tuần tự — duyệt đề xuất KPI và dashboard đọc lại số mới

Nguồn sự thật: `backend/app/routers/suggestions.py:72`, `backend/app/services/approval.py:46`
(`approve_kpi_suggestion`), `backend/app/services/dashboard.py:24` (`current_values`, `build_dashboard`),
`backend/app/rules.py:43` (`evaluate_kpi`), `frontend/src/pages/ReviewPage.tsx`, `frontend/src/lib/useAsync.ts`.

```mermaid
sequenceDiagram
    autonumber
    actor FE as ReviewPage.tsx
    participant API as routers/suggestions.py
    participant SVC as services/approval.py
    participant DASH as services/dashboard.py + rules.py
    participant DB as SQLite<br/>SQLAlchemy Session

    FE->>API: POST /api/suggestions/kpi/{id}/approve<br/>final_kpi_id, final_delta, note
    Note over API: Pydantic KpiApproveIn<br/>final_delta allow_inf_nan = False<br/>inf hoặc NaN thì 422 ngay tại biên

    API->>SVC: approve_kpi_suggestion db, suggestion_id,<br/>final_kpi_id, final_delta, note

    SVC->>DB: db.get KpiUpdateSuggestion, suggestion_id
    alt không tìm thấy
        DB-->>SVC: None
        SVC-->>API: raise NotFoundError
        API-->>FE: 404
    else status không còn pending
        DB-->>SVC: suggestion approved hoặc rejected
        SVC-->>API: raise ConflictError
        API-->>FE: 409 Đề xuất này đã được xử lý
        Note over DB: Chặn cộng delta hai lần
    end

    SVC->>DB: db.get Kpi, final_kpi_id
    alt KPI không tồn tại
        SVC-->>API: raise NotFoundError
        API-->>FE: 404
    end
    SVC->>SVC: math.isfinite final_delta
    alt không hữu hạn
        SVC-->>API: raise InvalidInputError
        API-->>FE: 422
        Note over SVC: Cổng thứ hai, sau Pydantic.<br/>Chặn cả đường gọi service trực tiếp
    end

    rect rgb(235, 245, 255)
        Note over SVC,DB: MỘT giao dịch — commit cùng nhau hoặc rollback cùng nhau
        SVC->>DB: suggestion.final_kpi_id = final_kpi_id<br/>final_delta, review_note<br/>status = approved<br/>reviewed_at = utcnow
        SVC->>DB: lazy load suggestion.report để lấy week_start
        SVC->>DB: db.add KpiProgressEntry<br/>kpi_id = final_kpi_id<br/>delta_value = final_delta<br/>source_suggestion_id = suggestion.id<br/>effective_date = report.week_start
        SVC->>DB: db.commit
        alt commit thất bại
            DB--xSVC: Exception
            SVC->>DB: db.rollback
            SVC-->>API: raise
            Note over DB: Không bao giờ có suggestion approved<br/>mà sổ cái thiếu dòng tương ứng
        end
    end

    SVC->>DB: db.refresh suggestion
    SVC-->>API: KpiUpdateSuggestion
    API-->>FE: 200 KpiSuggestionOut

    FE->>API: queue.reload → GET /api/suggestions?status=pending
    API-->>FE: SuggestionQueueOut, dòng vừa duyệt đã biến mất

    Note over FE: Người dùng chuyển sang trang Dashboard
    FE->>API: GET /api/dashboard
    API->>DASH: build_dashboard db, today = date.today
    DASH->>DB: SELECT kpi_id, SUM delta_value<br/>FROM kpi_progress_entries<br/>GROUP BY kpi_id
    DB-->>DASH: tổng delta đã duyệt của từng KPI
    DASH->>DB: SELECT kpis ORDER BY id
    loop mỗi KPI
        DASH->>DASH: evaluate_kpi target_value, actual_value,<br/>period_start, period_end, today
        Note over DASH: elapsed_ratio, expected_value<br/>at_risk = expected > 0 và actual < 0.8 * expected<br/>status = completed / at_risk / on_track
    end
    DASH-->>API: list DashboardItem
    API-->>FE: 200 list DashboardItemOut<br/>actual_value đã bao gồm delta vừa duyệt
```

## Giải thích

- **Không có cột nào bị "cập nhật tiến độ".** Duyệt chỉ ghi **thêm** một dòng vào sổ cái
  `kpi_progress_entries`. Dashboard đọc ra số mới vì `current_values()` cộng lại toàn bộ sổ cái
  mỗi lần gọi — không có cache, không có cột `current_value` để lệch.
- **Ranh giới giao dịch chính xác là khối `try` trong `approve_kpi_suggestion`** (`approval.py:62-79`).
  Đổi `status` và `db.add(KpiProgressEntry(...))` nằm trong cùng một `db.commit()`; bất kỳ lỗi nào
  cũng `db.rollback()` rồi ném lại.
- **Ba cổng kiểm tra chạy *trước* khi mở giao dịch**: suggestion còn `pending`, `final_kpi_id` tồn tại,
  `final_delta` hữu hạn. Nhờ vậy không có mutation nửa vời nào phải hoàn tác trong các ca lỗi thường gặp.
- **`final_delta` được kiểm hai lần** — một lần bởi Pydantic ở biên HTTP, một lần bởi `math.isfinite`
  trong service. Cả hai đều cho 422, nhưng cổng thứ hai còn bảo vệ khi service được gọi trực tiếp (test).
- **`effective_date` lấy từ `suggestion.report.week_start`**, không phải ngày duyệt — dòng sổ cái
  được ghi nhận vào đúng tuần báo cáo.
- **Dashboard không giữ trạng thái cũ.** `useAsync` cố tình không cache: mỗi `reload()` là một lần
  gọi mạng mới, nên sau khi duyệt không bao giờ thấy số cũ.

## Chỗ đã đồng bộ

1. **`final_kpi_id` khác `null`.** Spec §7.4 nói "bắt buộc", code không có `if` tường minh —
   ràng buộc đến từ kiểu `final_kpi_id: int` trong `KpiApproveIn`. **Đã sửa spec theo code:**
   §7.4 giờ nói rõ ràng buộc đến từ đâu, và rằng gọi thẳng service với `None` cho 404 chứ
   không phải 422.
2. **Cổng `math.isfinite` thứ hai** trong `approval.py:57` mà spec không mô tả — chặt hơn
   spec, không lỏng hơn. **Đã sửa spec theo code:** §7.4 giờ mô tả cả hai cổng.

## Còn lại, đã ghi nhận chứ chưa sửa

- `db.refresh(suggestion)` sau `commit` trong khi `sessionmaker` đặt `expire_on_commit=False`
  (`db.py:17`) — một vòng SELECT thừa. Không sai, chỉ thừa; ba service mới
  (`employee`/`kpi`/`task`) cố ý giữ cùng idiom để cả tầng `services/` nhất quán.
