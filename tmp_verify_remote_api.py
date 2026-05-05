
from pathlib import Path
p = Path(r"D:\JCY5001_clean\JCY5001AS_Clean_Source\remote_api.py")
text = p.read_text(encoding='utf-8', errors='ignore')
needles = [
    'current_state = get_state()',
    'control_widget.start_test.emit()',
    'logger.info(f"Test started via remote API (channel={channel})")'
]
for n in needles:
    print(n, n in text)
