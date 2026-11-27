#!/bin/bash
# LUMIERE GEN System - 대시보드 켜기(맥). 이미 켜져 있으면 브라우저만 엽니다.
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! curl -s -m 2 -o /dev/null http://localhost:8431/api/projects; then
  if [ ! -x .venv/bin/python ]; then
    echo "아직 설치 전이에요."
    echo "Claude 앱 [Code] 탭에서 이 폴더를 열고 \"설치해 줘\"라고 말해 주세요."
    read -n 1 -s -r -p "아무 키나 누르면 닫혀요"
    exit 1
  fi
  mkdir -p work
  nohup .venv/bin/python dashboard/server.py >> work/dashboard.log 2>&1 &
  sleep 4
fi
open http://localhost:8431/
