# 변환 도구 (게임에 넣지 않습니다)

발컨 Guidelime 가이드(ebfks1/Balcon_Guidlime_Horde_Forever)를 Polestar 팩으로 바꾸는 스크립트입니다.

- `convert.py` — 변환 본체. 입력: 발컨 저장소의 한/영 가이드, Polestar 애드온의 QuestDB·TravelData.
- `psdata.py` — Polestar 애드온 자료(퀘스트·NPC·비행 지점·여관) 읽기.
- `validate.py` — 만든 애드온을 Lua 5.1 로 불러 Polestar 팩 규격에 대조 (`pip install lupa`).
- `Setup.lua` — 처음 접속 때 Polestar 옵션을 맞추는 파일의 원본.
- `show.py` — 변환 결과 확인용.

스크립트 안의 경로(`/home/claude/...`)는 만든 환경 기준이라, 다른 곳에서 돌릴 때는 맞게 바꿔야 합니다.
지금 출력은 자체 변환기가 직접 쓴 애드온입니다. 공개판은 Polestar 공식 컴파일러(`forge guide compile`)로 빌드하는 방식으로 바꿀 예정입니다.
