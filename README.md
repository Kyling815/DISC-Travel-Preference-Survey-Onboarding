# Khảo sát Khởi tạo Sở thích Du lịch DISC

Đây là nguyên mẫu nghiên cứu ngoại tuyến, có tính xác định, dùng để khởi tạo sở thích du lịch cho người dùng mới. Hệ thống phân biệt rõ ba lớp thông tin:

1. Mức độ quan trọng của nhóm dịch vụ: lưu trú, nhà hàng, chuyến bay, điểm tham quan và di chuyển địa phương.
2. Tiêu chí ra quyết định: mức độ phù hợp thuộc tính, đánh giá, ngân sách, tính đa dạng và tính tập trung về địa lý.
3. Sở thích ngữ nghĩa và hoạt động: chủ đề, phạm vi khám phá, mật độ hoạt động, số lượng điểm tham quan và khả năng chấp nhận thời gian di chuyển.

Thí nghiệm đối chứng đi kèm cung cấp cho một người dùng khám phá chuyên biệt và một người dùng khám phá tổng quát cùng một bộ câu trả lời cho bảy câu hỏi. Vì vậy, hai người có vector trọng số nhóm dịch vụ hoàn toàn giống nhau. Tuy nhiên, tiêu chí độc lập, chủ đề và thiết lập hoạt động khác nhau khiến họ nhận được các đề xuất khác nhau từ cùng một thuật toán xếp hạng.

Toàn bộ hồ sơ người dùng và dữ liệu điểm tham quan trong dự án đều là dữ liệu tổng hợp. Hệ thống không sử dụng dịch vụ mạng, cơ sở dữ liệu bên ngoài, xác thực, API trả phí, LLM hoặc GPU.

## Onboarding v2: Prompt kết hợp DISC Travel Quiz

Workflow mới tiếp nhận prompt tự nhiên của người dùng, trích xuất ràng buộc và bằng chứng sở thích bằng bộ phân tích ngoại tuyến, sau đó dùng quiz bảy bước để xác nhận và tạo `Initial Preference State` trước khi bắt đầu PTS:

```text
Prompt → Prompt Prior → Quiz 7 bước → Evidence Fusion → User Confirmation → PTS Initial State
```

- Q1–Q3 chỉ đánh giá phong cách ra quyết định DISC.
- Q4 phân bổ 100 điểm Category.
- Q5 chọn hai Category cần bảo toàn khi phải đánh đổi.
- Q6 gồm bốn cặp đánh đổi Criterion.
- Q7 xác nhận scope, mật độ, số hoạt động và giới hạn di chuyển.

DISC không đóng góp vào Category hoặc Criterion Weights. Category fusion sử dụng 25% prompt, 55% phân bổ Q4 và 20% lựa chọn Q5. Criterion fusion sử dụng 30% prompt, 60% Q6 và 10% bằng chứng hỗ trợ từ Q7. Mọi hệ số và đóng góp được lưu trong `provenance`.

Prompt parser phân biệt:

- Ràng buộc cứng: điểm đi/đến, số người, thời lượng và tổng ngân sách.
- Sở thích rõ ràng: chủ đề điểm tham quan, ẩm thực và các category được nhấn mạnh.
- Suy luận độ tin cậy thấp hơn: scope, mật độ và compactness.

Chạy ví dụ Đà Nẵng và xuất trạng thái sẵn sàng cho PTS:

```powershell
python -m scripts.run_onboarding_demo
```

Kết quả được ghi tại `outputs/pts_initial_state_example.json`.

## Cài đặt

Yêu cầu Python 3.11 trở lên. Chạy các lệnh sau tại thư mục dự án:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -X utf8 -m pip install -r requirements.txt
```

Trên macOS/Linux, kích hoạt môi trường bằng `source .venv/bin/activate`.

Nếu Windows không nhận lệnh `python` nhưng đã cài Python Launcher, có thể thay `python` bằng `py`. Tùy chọn `-X utf8` giúp `pip` xử lý đúng đường dẫn dự án có ký tự tiếng Việt.

## Chạy hệ thống

Tạo nhóm người dùng mô phỏng có tính xác định và các tệp xuất dạng bảng:

```powershell
python -m scripts.generate_users
```

Tạo toàn bộ tệp kết quả và báo cáo đánh giá Markdown:

```powershell
python -m scripts.run_evaluation
```

Khởi động API. Tài liệu OpenAPI tương tác được cung cấp tại `/docs`:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Sau khi khởi động, mở `http://127.0.0.1:8001/docs`. Có thể chọn cổng khác nếu `8001` đang được một ứng dụng khác sử dụng. Cổng mặc định `8000` thường có thể xung đột với Apache hoặc dịch vụ web cục bộ.

Khởi động bảng điều khiển:

```powershell
streamlit run dashboard/streamlit_app.py
```

Chạy kiểm thử tự động:

```powershell
pytest -q
```

## API

| Phương thức | Đường dẫn | Chức năng |
|---|---|---|
| GET | `/health` | Kiểm tra trạng thái hoạt động của dịch vụ |
| GET | `/questions` | Trả về bảng khảo sát bảy câu hỏi được cấu hình bằng dữ liệu |
| GET | `/onboarding/start-quiz` | Trả về cấu hình quiz onboarding v2 gồm bảy bước |
| POST | `/onboarding/prompt/analyze` | Phân tích prompt và tạo Category/Criterion prior tạm thời |
| POST | `/onboarding/finalize` | Hợp nhất prompt, quiz và xác nhận thành PTS Initial State |
| POST | `/onboarding/score` | Tính phân bố DISC, điểm nhóm thô, trọng số chuẩn hóa và phần giải thích |
| POST | `/preferences/criterion` | Ước lượng tiêu chí độc lập hoặc chuẩn hóa trọng số do người dùng ghi đè |
| POST | `/initial-state` | Tạo trạng thái người dùng ban đầu đã được kiểm tra và có thể xuất dữ liệu |
| POST | `/simulation/generate` | Tạo nhóm mô phỏng có tính xác định và đáp ứng ngưỡng bắt buộc |
| GET | `/simulation/users` | Lấy nhóm mô phỏng hiện tại hoặc nhóm mặc định |
| POST | `/recommendations/compare` | So sánh cặp người dùng đối chứng hoặc hai hồ sơ được cung cấp |
| GET | `/evaluation/summary` | Lấy các chỉ số đánh giá và kiểm tra hợp lệ |

Ví dụ yêu cầu tính điểm:

```json
{
  "answers": {
    "q1": "A", "q2": "A", "q3": "A",
    "q4": "D", "q5": "D", "q6": "D", "q7": "D"
  }
}
```

ID câu hỏi không hợp lệ, ID câu trả lời không hợp lệ, khóa vector sai, trọng số ghi đè âm, dữ liệu đầu vào không đúng định dạng và giá trị enum không được hỗ trợ đều nhận phản hồi lỗi kiểm tra dữ liệu có mô tả rõ ràng.

## Quy tắc ánh xạ và đề xuất

Quá trình tính trọng số nhóm bắt đầu bằng vector tiên nghiệm gồm toàn số 1, sau đó cộng bằng chứng được cấu hình trong `app/data/questions.json`. Mã nguồn không chứa logic tính điểm riêng cho từng câu hỏi.

Khi mô phỏng, một hồ sơ chỉ được chấp nhận nếu trọng số nhóm chuẩn hóa lớn nhất đạt ít nhất `0.30`. Nếu không đạt, hệ thống loại hồ sơ đó và lấy mẫu lại cho đến giới hạn số lần thử. Câu trả lời của người dùng tương tác thực tế không bao giờ bị thay đổi hoặc từ chối bởi quy tắc chỉ dành cho mô phỏng này.

Quá trình tính trọng số tiêu chí sử dụng một vector tiên nghiệm dương độc lập. Các chủ đề được chỉ định và phạm vi chuyên biệt làm tăng tầm quan trọng của mức độ phù hợp thuộc tính. Phạm vi tổng quát làm tăng tầm quan trọng của tính đa dạng. Mức ưu tiên đánh giá và ngân sách được ánh xạ trực tiếp tới tiêu chí tương ứng, còn sở thích di chuyển được ánh xạ tới tính tập trung về địa lý.

Mật độ hoạt động có thể bổ sung một lượng nhỏ bằng chứng cho tính đa dạng hoặc tính chọn lọc, nhưng số lượng điểm tham quan mong muốn vẫn được lưu thành trường riêng. Hệ thống cũng hỗ trợ người dùng cung cấp đầy đủ vector trọng số tiêu chí để ghi đè sau khi vector được kiểm tra và chuẩn hóa.

Quá trình đề xuất sử dụng các đặc trưng ứng viên đã chuẩn hóa trong khoảng `0–1` và tích vô hướng với trọng số tiêu chí. Thuật toán chọn tham lam để tính lại tính đa dạng biên và tính tập trung khi hành trình được mở rộng. Giới hạn thời gian di chuyển tối đa được áp dụng trước khi xếp hạng ứng viên.

Khoảng cách di chuyển được tính theo công thức Haversine trên đường thẳng và chuyển đổi bằng vận tốc giả định `30 km/h`. Đây chỉ là giá trị xấp xỉ, không phải thời gian di chuyển chính xác theo mạng lưới đường bộ.

## Khả năng tái lập và các tệp kết quả

Hai archetype đầu tiên sử dụng cùng chuỗi câu trả lời `A,A,A,D,D,D,D`. Chuỗi này tạo ra vector điểm thô `(1, 5, 1, 16, 2.5)`. Vì vậy, vector trọng số nhóm dùng chung thực sự được suy ra từ bảng câu hỏi, không phải được chỉnh sửa thủ công. Seed dùng để mô phỏng được lưu trong metadata của từng người dùng.

Lệnh `python -m scripts.run_evaluation` tạo ra các tệp sau:

- `outputs/simulated_users.json`
- `outputs/simulated_users.csv`
- `outputs/category_weights.csv`
- `outputs/criterion_weights.csv`
- `outputs/recommendation_comparison.json`
- `outputs/evaluation_summary.json`
- `outputs/evaluation_report.md`

## Kiểm thử

Bộ kiểm thử tự động xác minh:

- Tính nhất quán của quá trình chấm bảy câu hỏi.
- Trọng số nhóm và trọng số tiêu chí không âm, có tổng bằng 1.
- Mô phỏng có tính xác định với seed cố định.
- Mỗi người dùng mô phỏng có ít nhất một trọng số nhóm đạt `0.30`.
- Nhóm mô phỏng chứa ít nhất năm người dùng.
- Cặp đối chứng có cùng câu trả lời và trọng số nhóm nhưng khác tiêu chí và sở thích ngữ nghĩa.
- Đề xuất cho người dùng chuyên biệt và tổng quát thực sự khác nhau.
- Giới hạn di chuyển cứng được áp dụng.
- Hồ sơ có thể xuất thành JSON hợp lệ.
- API kiểm tra và từ chối dữ liệu đầu vào không hợp lệ.
- Câu trả lời của người dùng thực tế không bị sửa để thỏa mãn ngưỡng mô phỏng.
- Prompt tiếng Việt được trích xuất đúng ràng buộc và semantic preferences.
- DISC v2 không làm thay đổi Category hoặc Criterion Weights.
- Trạng thái onboarding v2 có confidence, provenance và cờ `ready_for_pts`.

## Hạn chế

- Ánh xạ từ DISC sang sở thích du lịch mang tính heuristic và không phải là phương pháp suy luận tính cách đã được kiểm chứng khoa học.
- Người dùng tổng hợp không phải người dùng thực tế; dữ liệu điểm tham quan tổng hợp không thể chứng minh độ chính xác trong thế giới thực.
- Thời gian di chuyển là giá trị xấp xỉ hình học, không phải kết quả định tuyến.
- Nguyên mẫu chỉ minh họa cách biểu diễn sở thích và hành vi xếp hạng có tính xác định.
- Dự án không huấn luyện hoặc giả lập DQN và không tuyên bố chứng minh khả năng cá nhân hóa tốt hơn.
