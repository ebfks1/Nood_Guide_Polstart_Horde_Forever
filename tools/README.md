# 변환 도구 (게임에 넣지 않습니다)

발컨 Guidelime 가이드(ebfks1/Balcon_Guidlime_Horde_Forever)에서 Polestar 팩 원본(`packs/*/pack.json`, `.guide`)을 만드는 스크립트입니다.

- `emit_guide.py` — 실행 파일. `python3 emit_guide.py <packs 폴더> <버전>` → `nood`(영어), `nood-ko`(한국어) 원본을 씁니다.
- `convert.py` — 발컨 가이드 한 줄 한 줄을 단계·목표로 바꾸는 본체 (레벨+4 자동 건너뛰기 규칙 포함).
- `psdata.py` — Polestar 애드온 자료(퀘스트·NPC·비행 지점·여관) 읽기.
- `validate.py`, `show.py` — 예전 자체 빌드 확인용.
- `polestar.ref` — 빌드에 쓰는 Polestar 저장소 커밋(공식 컴파일러와 참조 데이터의 기준).

스크립트 안의 경로(`/home/claude/...`)는 만든 환경 기준이라, 다른 곳에서 돌릴 때는 맞게 바꿔야 합니다.
애드온 자체는 이 스크립트가 아니라 Polestar 공식 컴파일러(`forge guide lint`, `forge release pack`)가 GitHub Actions 에서 만듭니다.
