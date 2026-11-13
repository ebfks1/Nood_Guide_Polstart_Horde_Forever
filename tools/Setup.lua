-- Nood Guide @VERSION@ for Polestar: sets a few Polestar options once, so the guide behaves like the Guidelime BalCon guide it is based on.
-- Nood 가이드: 발컨 가이드처럼 동작하도록 Polestar 옵션 몇 가지를 처음 한 번만 맞춥니다.
--   /nood                       다시 적용 · apply again
--   /nood undo (되돌리기)        바꾸기 전 값으로 · back to the values from before
local KO = GetLocale and GetLocale() == "koKR"
local TAG = "|cffffd200" .. "Nood" .. "|r: "

-- { Polestar setting, value, what it does }
local WANT = {
	{ "behavior.suggestFrom", "nood",
		"가이드 추천을 Nood 가이드에서 가져옵니다", "guide suggestions come from Nood Guide" },
	{ "ui.instance", "show",
		"던전 안에서도 가이드 창을 보여 줍니다", "the guide window stays visible inside dungeons" },
	{ "ui.notesOpen", true,
		"단계 설명을 처음부터 전부 펼쳐 보여 줍니다", "step tips start opened in full" },
	{ "ui.upcoming", 3,
		"다음 단계 3개를 미리 보여 줍니다", "the next 3 steps are listed under the current one" },
	{ "ui.upcomingOpen", true,
		"다음 단계 목록을 펼친 채로 둡니다", "the list of next steps starts opened" },
	{ "behavior.closeSkipped", false,
		"가이드에 없는 퀘스트 창을 자동으로 닫지 않습니다", "quest windows the guide does not use are not closed for you" },
}

local function ready()
	return type(Polestar) == "table" and type(Polestar.Get) == "function" and type(Polestar.Set) == "function"
end

local function apply(again)
	if not ready() then return end
	NoodGuideDB = type(NoodGuideDB) == "table" and NoodGuideDB or {}
	local db = NoodGuideDB
	if db.applied and not again then return end
	db.prev = type(db.prev) == "table" and db.prev or {}
	print(TAG .. (KO and "Polestar 옵션을 Nood 가이드에 맞췄습니다 (되돌리기: /nood undo)" or "Polestar options set for Nood Guide (to undo: /nood undo)"))
	for _, w in ipairs(WANT) do
		local path, value = w[1], w[2]
		local ok, now = pcall(Polestar.Get, path)
		if ok and now ~= value then
			if db.prev[path] == nil then db.prev[path] = { v = now } end
			pcall(Polestar.Set, path, value)
			print("  - " .. (KO and w[3] or w[4]))
		end
	end
	db.applied = 1
end

local function undo()
	if not ready() then return end
	local db = type(NoodGuideDB) == "table" and NoodGuideDB or {}
	for path, old in pairs(type(db.prev) == "table" and db.prev or {}) do
		pcall(Polestar.Set, path, old.v)
	end
	db.prev = {}
	print(TAG .. (KO and "Polestar 옵션을 바꾸기 전 값으로 되돌렸습니다." or "Polestar options are back to their values from before."))
end

local f = CreateFrame("Frame")
f:RegisterEvent("PLAYER_LOGIN")
f:SetScript("OnEvent", function() apply(false) end)

SLASH_NOODGUIDE1 = "/nood"
SLASH_NOODGUIDE2 = "/noodguide"
SlashCmdList["NOODGUIDE"] = function(msg)
	msg = (msg or ""):lower()
	if msg:find("undo", 1, true) or msg:find("되돌리기", 1, true) then undo() else apply(true) end
end
