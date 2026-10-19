#!/bin/zsh
cd -- "${0:A:h}" || exit 1
PYTHON=".build/national-analysis-venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  print 'ยังไม่มี Python environment โปรดอ่าน docs/setup/MAC_SETUP_TH.md'
  read '?กด Enter เพื่อปิด'
  exit 1
fi
"$PYTHON" tools/open_orchard_report.py
if [[ $? -ne 0 ]]; then
  read '?เปิดรายงานไม่สำเร็จ กด Enter เพื่อปิด'
fi
