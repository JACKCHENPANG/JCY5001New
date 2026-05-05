
from pathlib import Path
text = Path(r"D:\JCY5001_clean\JCY5001AS_Clean_Source\logs\app.log").read_text(encoding='utf-8', errors='ignore')
for stamp in ['2026-05-05 19:30:', '2026-05-05 19:46:']:
    print('===', stamp, '===')
    for ln in text.splitlines():
        if stamp in ln and any(k in ln for k in [
            'start_test', 'Test started via remote API', 'test_control', '_on_start_test',
            '统一测试控制器', '测试工作线程', '并行错频测试', 'staggered_test_executor',
            'execute_high_frequency_test', '开始高频点错频测试', '执行第', '高频点错频测试完成',
            '测试执行完成', 'is_testing', '用户停止'
        ]):
            print(ln.encode('ascii','backslashreplace').decode('ascii'))
