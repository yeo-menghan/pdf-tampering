# pdf-tampering

Exploring use cases for pdf tampering

Looking at xref: https://pypdf2.readthedocs.io/en/3.x/dev/pdf-format.html
- On MAC: exporting as a linearised PDF or PDF-A (Archiving) will remove the xref history
- Linearizing a PDF—also called “Fast Web View”—means rewriting it in a special order so that the first page can be displayed before the whole file is downloaded. This requires a full rewrite of the PDF file, not just an incremental update.
- TODO: check if flattening a pdf (on PDF Acrobat) on windows constitute a full-rewrite or incremental change


Metadata

## Setting up

1. uv set-up

Mac
```bash
uv sync
source .venv/bin/activate
```
Windows
```powershell
uv sync
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\activate.ps1
```

2. installing detectron2
```powershell
wsl
pip install 'git+https://github.com/facebookresearch/detectron2.git'
```
