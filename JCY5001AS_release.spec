# -*- mode: python ; coding: utf-8 -*-


from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect matplotlib backends explicitly
extra_datas = collect_data_files('matplotlib.backends')
extra_hidden = collect_submodules('matplotlib.backends')
# ===== 编译配置 =====
# 构建号：每次发布+1
BUILD_NUMBER = "56"

a = Analysis(
    ['main.py'],
    pathex=[r'D:\\JCY5001_clean\\JCY5001AS_Clean_Source'],
    binaries=[],
    datas=[
        ('remote_api.py', '.'),
        ('jcy5001_mcp_server.py', '.'),
        ('startup_resource_check.py', '.'),
        ('config/app_config.json', 'config'),
        ('resources', 'resources'),
        ('templates', 'templates'),
        ] + extra_datas,
    hiddenimports=[
        'PyQt5.QtChart',
        'PyQt5.QtWidgets',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'scipy',
        'scipy.signal',
        'scipy.interpolate',
        'scipy.optimize',
        'scipy.stats',
        'scipy.fft',
        'PIL',
        'matplotlib',
        'matplotlib.backends.backend_qt5agg',
        'cryptography',
        
        'mcp',
        
        'pydantic',
        
        'annotated_types',
        'remote_api',
        'jcy5001_mcp_server',
        'startup_resource_check',
        'flask',
        'werkzeug',
        'jinja2',
        'markupsafe',
        'click',
        'itsdangerous',
        'blinker'] + extra_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'torchvision', 'torchaudio', 'torchgen', 'torchmetrics',
        'transformers', 'tokenizers', 'safetensors', 'huggingface_hub',
        'accelerate', 'datasets', 'diffusers', 'peft',
        'onnx', 'onnxruntime', 'ml_dtypes',
        'tensorflow', 'keras',
        'tkinter', 'PyQt6', 'PySide2', 'PySide6',
        'pytorch_lightning', 'lightning_fabric', 'lightning_utilities',
        'pytest', '_pytest',
        'sklearn', 'joblib',
        'pandas', 'openpyxl', 'xlrd',
        'plotly', 'bokeh', 'dash',
        'jupyter', 'ipykernel', 'ipywidgets', 'notebook',
        'sentencepiece', 'regex',
        'tqdm', 'rich',
        'cffi', 'pycparser',
        'aiohttp', 'yarl', 'multidict',
        'greenlet', 'eventlet',
        'networkx', 'sympy',
        'einops', 'tabulate',
        'gunicorn', 'waitress',
        'psycopg2', 'SQLAlchemy',
        'lxml', 'bs4', 'soupsieve',
        'reportlab', 'docx',
        'dateutil', 'pytz',
        'pyarrow', 'fsspec',
        'h5py', 'av',
        'debugpy', 'ipython',
        'zmq', 'tornado',
        'sphinx', 'alabaster',
        'babel', 'snowballstemmer',
        'opentelemetry',
        'authlib',
        'functorch',
        'einops',
        'compression',
        'pkg_resources', 'setuptools',
        'Cython', 'pyximport',
        'jsonschema', 'rpds', 'referencing',
        'argcomplete', 'traitlets',
        'wcwidth', 'prompt_toolkit',
        'jedi', 'parso', 'stack_data', 'pure_eval', 'executing', 'asttokens',
        'pygments',
        'pyinstaller',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
EXE_NAME = 'JCY5001AS' + BUILD_NUMBER
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=EXE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=EXE_NAME,
)
