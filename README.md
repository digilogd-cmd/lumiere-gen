# LUMIÈRE GEN (뤼미에르 젠)

**이야기만 넣으면, 영상이 나옵니다.** 주제나 대본을 넣으면 내 PC의 Claude가 대본·콘티를 짜고, Google Flow로 그림·영상·음악을, Google AI Studio로 성우 목소리를 만들어 자막·썸네일까지 붙인 완성 영상을 냅니다. API 키 없이, 내 크롬에 로그인된 내 계정으로 돌아가요.

- 스토리 애니메이션 · 숏 드라마 · 설명 영상 · 쇼츠(9:16)
- 13단계 자동 제작 + 단계마다 품질 검문
- "3번 장면 더 어둡게" 처럼 말로 고치기, 가벼운 편집
- 내 스타일(색·글꼴·썸네일) 기억하기

자세한 능력: [할_수_있는_것.md](할_수_있는_것.md)

## 받기
오른쪽 **Releases** 에서 `LUMIERE_GEN_<버전>.zip` 을 받아 압축을 푸세요. **윈도우·맥 공용** 한 파일이에요(한글·공백 없는 경로 권장, 예: 윈도우 `C:\LUMIERE_GEN` · 맥 `~/LUMIERE_GEN`).
코드만 보려면 이 저장소를 그대로 받아도 됩니다.

## 설치 (약 20~40분)
1. Claude 데스크톱 앱 → **Code** 탭에서 이 폴더를 엽니다.
2. "설치해 줘" 라고 말하면 Claude가 Python·ffmpeg·Node.js를 점검하고 필요한 것만 설치한 뒤 자가 검사까지 합니다.
3. 크롬에 Claude in Chrome 확장을 깔고 Google Flow·AI Studio에 직접 로그인합니다.
4. 윈도우 `LUMIERE_GEN_시작.bat` / 맥 `LUMIERE_GEN_시작.command` → 대시보드에서 시작.

맥은 Homebrew 로 설치하고(없으면 Claude가 터미널에 붙여 넣을 한 줄을 알려 줘요), 폴더 안 가상환경(`.venv`)에서 돌아요.

## 필요한 것
Windows 10/11 또는 macOS 13+(애플 칩 권장, **맥은 시험판**) · Claude Pro 이상 구독 + Claude 데스크톱 앱 · Google 계정(Flow·AI Studio) · 크롬 · 여유 공간 20GB 이상. NVIDIA 그래픽카드가 있으면 받아쓰기가 빨라요.

## 사용권
**개인용·비상업 무료.** 되팔기·유료 상품에 넣기·회사 업무용·이름 바꿔 배포는 금지입니다. 만든 영상의 권리는 사용자에게 있어요. → [LICENSE](LICENSE) · [사용권.txt](사용권.txt)

문의: artgourmet.official@gmail.com
