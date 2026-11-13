# Nood 가이드 — 던전 레벨업 (WoW 포에버 · 호드 1-60) · Polestar용

Polestar 애드온용 커뮤니티 가이드 팩입니다. Polestar가 있어야 동작합니다.
던전에 갈 레벨이 되면 그 던전을 먼저 다녀오고, 다음 던전 레벨이 될 때까지는 효율 좋은 지역 퀘스트만 합니다.
Guidelime용 발컨(BalCon) 던전 레벨업 가이드를 참고해 만들었습니다.

- CurseForge Project ID: 1801649
- Polestar 제작진이 만든 가이드가 아닙니다. 문의·오류 제보는 이 저장소의 Issues 로 해 주세요.

## 구성
- `packs/nood` (영어) · `packs/nood-ko` (한국어): 가이드 원본(`pack.json` + `.guide`). Polestar 공식 컴파일러(`forge`)가 애드온으로 빌드합니다.
- `setup/NoodGuide_Setup`: 처음 접속 때 Polestar 옵션 몇 가지를 맞추는 작은 애드온 (`/nood undo` 로 되돌리기).
- `tools/`: 발컨 Guidelime 가이드에서 `.guide` 원본을 만드는 변환 스크립트 (게임에 넣지 않음).
- `build` 브랜치: GitHub Actions 가 올리는 빌드 결과(검사 로그, 컴파일된 애드온 폴더).

## 배포 방법
`packs/nood/pack.json` 과 `packs/nood-ko/pack.json` 의 `version` 을 새 번호로 바꿔 main 에 올리면
GitHub Actions 가 공식 컴파일러로 검사·빌드하고, 오류가 없으면 태그(v번호)를 만들어 커스포지에 올립니다.
번호에 `-beta` 가 붙으면 Beta, 없으면 Release, `-dev` 가 붙으면 빌드만 하고 배포하지 않습니다.

---

# Nood Guide — Dungeon Leveling (WoW Forever, Horde 1-60) for Polestar

A community guide pack for the Polestar addon. Polestar is required.
You run each dungeon as soon as you reach its level; between dungeons you only do the most efficient zone quests.
Based on the Guidelime guide BalCon Dungeon Leveling.

- This pack is not made by the Polestar team. Please report problems in this repository's Issues.
