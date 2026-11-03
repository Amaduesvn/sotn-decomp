# SOTN PS1 US — Quy ước Việt hóa

**Phiên bản mục tiêu:** PlayStation 1 US, SLUS-00067.  
**Trạng thái:** Bản dịch nháp. Chưa có font tiếng Việt hoạt động trong game.

## Danh xưng và thuật ngữ

| Nguồn | Cách dùng dự kiến | Lưu ý |
| --- | --- | --- |
| Alucard, Richter Belmont, Maria, Dracula | Giữ nguyên | Tên riêng nhân vật |
| ALUCART / alucart | Giữ nguyên | Tên cố ý khác Alucard; không tự sửa |
| Death | Death | Tên boss; chỉ dùng 'Thần Chết' khi văn cảnh thật sự là danh từ chung |
| Olrox, Granfaloon, Galamoth, Cerberus, Medusa | Giữ nguyên | Kiểm tra nhất quán với bảng tên quái khi trích xuất |
| Doppleganger (đúng theo bản US) | Doppelganger (dự kiến) | Có khác biệt chính tả; cần quyết định sau khi kiểm tra tên quái |
| Familiar | Trợ thủ | Dùng chung cho Dơi, Ma, Tiên, Quỷ, Kiếm |
| Faerie / Sprite | Tiên / Sprite | Phân biệt hai loại trợ thủ; không đánh đồng |
| Demon / Nosedevil | Quỷ / Quỷ mũi dài | Phân biệt hai loại trợ thủ |
| Relic | Di vật | Vật phẩm mở khóa khả năng |
| Spell | Phép thuật | Giao diện pháp thuật |
| Special Moves | Tuyệt kỹ | Tránh đồng nhất với bảng phép thuật |
| HP / MP / STR / CON / INT / LCK / EXP | Giữ ký hiệu | Tránh thay đổi ô thông số hẹp |
| Time Attack | Thử thách thời gian | Có thể rút gọn khi giới hạn bề rộng |
| Wolf / Bat / Mist | Sói / Dơi / Sương | Nhất quán ở phép thuật và relic |
| Holy Glasses | Kính Thánh | Kiểm tra sau với danh mục trang bị |

## Quy trình duyệt

- **draft**: Đã có phương án dịch, chưa được rà soát ngữ nghĩa/bố cục.
- **reviewed**: Đã kiểm tra ngữ cảnh, cách dùng, ký hiệu và độ dài dự kiến.
- **tested_in_game**: Chỉ dùng sau khi đã biên dịch và tận mắt xác minh trong PS1/giả lập.
- **preserve**: Có chủ đích giữ nguyên, ví dụ tên riêng hoặc tên chỉ số.
- **defer**: Tạm hoãn vì chưa rõ có hiển thị hay chỉ là chuỗi kỹ thuật.

## Yêu cầu kỹ thuật

1. Dùng Unicode NFC trong bảng dịch để tránh cùng một chữ có nhiều chuỗi mã khác nhau.
2. Không thay trực tiếp UTF-8 vào bộ mã PS1 hoặc dữ liệu Shift-JIS khi chưa có phương án font và encoder tương thích.
3. Giữ nguyên ID chuỗi, lệnh cutscene, tên trường, điều kiện và thứ tự script.
4. Kiểm tra rộng/hẹp thực tế; không đo dung lượng bằng số ký tự UTF-8 một cách giản đơn.
5. Các tên khu vực đã dịch toàn cụm, chưa chia vào hai phần hiển thị của bản gốc.
6. Không đưa BIN/CUE, ROM, BIOS, tài nguyên thương mại trích xuất vào repository.

## Những chỗ cần rà soát sau khi có dữ liệu game

- Mức độ hiện diện của chuỗi tiếng Nhật còn tồn tại trong bảng bản US.
- Tên quái vật, trang bị, skill tương ứng trong dữ liệu đã trích xuất để thống nhất thuật ngữ.
- Dấu câu và căn lề trong mô tả relic, menu và phần phụ đề.
- Hai bộ familiar đặc biệt Sprite/Nosedevil có được truy cập trên bản US hay không.
- Cách trình bày 25 tên khu vực bằng 1–2 dòng trên màn hình chọn tệp lưu.
