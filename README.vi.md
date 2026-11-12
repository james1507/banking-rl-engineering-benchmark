# Banking Transaction Debugging RL Lab

Project mới theo SRS: mô phỏng giao dịch ngân hàng và bộ bài tập sửa lỗi cho coding agent. Chỉ dùng tiền, tài khoản và dữ liệu giả lập.

## Mở và chạy

Yêu cầu: Docker Desktop đang chạy, Docker Compose v2, Git, Make, Python 3.9+ trên máy. Python 3.12 và dependencies chạy trong container.

```sh
cd /Users/cmc-macmini/projects/banking-rl-engineering-benchmark
make up
make seed
python3 scripts/demo.py
```

Mở [Swagger API](http://localhost:8010/docs). Tài khoản mẫu: `alice@example.test`, `bob@example.test`, `admin@example.test`; mật khẩu sinh ngẫu nhiên nằm ở `DEMO_PASSWORD` trong `.env` được Git bỏ qua. Dùng `/api/v1/auth/login`, rồi nhập access token vào **Authorize**. Chạy `scripts/demo.py` để chuyển 1 cent và kiểm tra gửi lại cùng khóa trả đúng kết quả cũ.

`make down` dừng dịch vụ, giữ dữ liệu. `make up` chạy lại. Port mặc định: API 8010, PostgreSQL 5440; chỉ mở trên localhost.

## Phần đã có

- FastAPI, PostgreSQL 16, Alembic; tiền số nguyên, sổ cái kép bất biến, chuyển tiền nguyên tử.
- JWT/Argon2, refresh token có phát hiện dùng lại, kiểm tra chủ tài khoản, chống gửi giao dịch trùng.
- Khóa đồng thời, phục hồi sau crash, lịch sử phân trang, đối soát độc lập.
- Outbox worker, retry/dead-letter, người thụ hưởng, hạn mức ngày UTC, API quản trị, metrics/logs/traces.
- Ba bài RL-01–03: bản lỗi, bản sửa, bộ chấm HTTP/SQL chạy cách ly, các bản đối chứng và bằng chứng chạy thật.

## Kiểm chứng

```sh
make ci
make security-check
make validate-tasks
make invariants
```

Kiểm thử dùng DB riêng, không xóa dữ liệu demo. Bộ chấm tạo môi trường riêng cho từng lượt; chạy lâu hơn kiểm thử ứng dụng. Xem [bằng chứng](docs/evidence/README.md), [kết quả bộ chấm](docs/evaluation-results.md) và [bảng nghiệm thu SRS](docs/acceptance-matrix.md).

Phạm vi nâng cao còn mở: RL-04–10, risk-review, giao diện React tùy chọn, tải 10k/100k, CI từ xa và HA/PITR. Đây là bản mô phỏng kỹ thuật chạy cục bộ; chưa phải hệ thống ngân hàng vận hành thực tế. Kiến trúc, hướng dẫn vận hành và giới hạn nằm trong [README đầy đủ](README.md).
