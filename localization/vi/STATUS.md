# SOTN Việt hóa PS1 — Trạng thái trước khi dùng BIN

Cập nhật: 2026-11-03. Nhánh: vi-localization. Mục tiêu: PlayStation US SLUS-00067.

## Những gì đã có và đã lưu trong repository

- Bảng nguồn có **225 mục chữ không rỗng** trong mã nguồn C: 105 menu/nhãn, 16 phép thuật, 60 tên và mô tả relic, 44 mảnh tên khu vực.
- **168 mục bản dịch nháp**, gồm 92 menu/nhãn, 16 phép thuật và 60 relic.
- **25 tên khu vực đầy đủ** (tương ứng 44 mảnh gốc), chưa chia lại thành hai dòng trong game.
- **13 mục menu** được phân loại giữ nguyên hoặc tạm hoãn có giải thích.
- Công cụ trích xuất script cutscene dạng YAML thành CSV và đưa bản dịch trở lại **file YAML thử nghiệm** mà giữ nguyên các dòng lệnh điều khiển. Chưa thể tạo script chạy PS1 vì còn thiếu encoder/font.
- Công cụ thống kê bảng font: 52/186 chữ cái tiếng Việt (bao gồm in hoa và dấu) có mặt; **134 chữ cái còn thiếu** trong mapping 8x8 của bản PS1.
- Công cụ đọc và kiểm tra sơ bộ BIN/CUE không làm thay đổi tệp nguồn.
- Các bài test offline trên GitHub Actions. Kết quả CI ở nhánh vi-localization là thước đo kiểm tra mã nguồn và bảng dịch, **không phải kiểm thử game**.

## Vì sao đến đây cần dữ liệu đĩa gốc

Repository decomp không chứa dữ liệu thương mại để biên dịch game. Phần lớn tên vũ khí, mô tả trang bị, dữ liệu quái, hội thoại còn phải được trích xuất từ game gốc. Quan trọng hơn, cần dữ liệu font/đồ họa thật để chọn phương án đưa dấu tiếng Việt vào các đường hiển thị PS1.

Cần **bản PS1 US SLUS-00067** do người dùng sở hữu, ưu tiên:

1. File **.cue** và file **.bin** mà CUE tham chiếu; nếu đĩa tách nhiều BIN thì cần tất cả track liên quan.
2. Không đưa file BIN/CUE vào repository công khai. Chỉ dùng trong môi trường thử nghiệm riêng.
3. Nếu tệp quá lớn để đính kèm, có thể chạy công cụ kiểm tra/trích xuất trên máy cá nhân và chia sẻ **kết quả kỹ thuật cần thiết** hoặc làm việc trong môi trường có quyền truy cập tệp.

Lệnh kiểm tra sơ bộ (không chỉnh sửa dữ liệu):

    python3 localization/vi/tools/disc_preflight.py "duong-dan/game.cue"

Lệnh tính SHA-256 toàn bộ file (đọc nhiều dữ liệu, lâu hơn):

    python3 localization/vi/tools/disc_preflight.py "duong-dan/game.cue" --sha256

Các bước sau khi có BIN/CUE:

1. Xác minh cấu trúc đĩa và phiên bản US. So khớp checksum bản hợp lệ nếu có.
2. Chạy quy trình trích xuất và build nguyên bản, kiểm tra file tái tạo.
3. Trích xuất toàn bộ bảng tên/mô tả vật phẩm, quái và script hội thoại.
4. Tạo bản thử font tiếng Việt có dấu; kiểm tra 8×8 và đường chữ mô tả Shift-JIS riêng.
5. Đưa thử một menu, một tên vật phẩm, một mô tả và một đoạn thoại ngắn vào build; kiểm tra trên DuckStation.
6. Sau khi thử nghiệm thành công mới tăng phạm vi, QA toàn bộ và đóng gói patch không chứa ROM.

## Giới hạn đã xác nhận

- **Không có patch Việt hóa chạy được tại thời điểm cập nhật này.**
- Dự án chưa sửa font của game hoặc thay dữ liệu văn bản trong bản PS1.
- Tỷ lệ 225/225 nguồn đã phân loại **không phải 100% nội dung của SOTN**.
- File YAML UTF-8 của công cụ cutscene staging **không được biên dịch trực tiếp** bằng builder hiện tại trước khi sửa cơ chế mã hóa.

## Bổ sung hỗ trợ CHD

- Đã bổ sung công cụ kiểm tra header CHD v3–v5, không cần giải nén để xem định dạng.
- Đã bổ sung công cụ chuyển CHD sang `disks/sotn.us.cue` và `disks/sotn.us.bin`
  bằng MAME `chdman`, luôn kiểm tra trước và từ chối ghi đè.
- Lệnh build chuẩn dựa trên hướng dẫn chính thức của sotn-decomp:
  `make extract_disk`, `make extract -j`, `make build -j`, `make check`.
- Đây là công cụ và kiểm thử **dùng mẫu dữ liệu giả lập**. Không có chứng cứ
  rằng một file CHD người dùng gửi đã được đọc hoặc chuyển đổi thành công.
- Chi tiết: [CHD_INSTRUCTIONS.md](CHD_INSTRUCTIONS.md).
