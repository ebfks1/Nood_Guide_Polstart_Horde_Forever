-- Nood Guide for Polestar (NoodGuide_Setup): sets a few Polestar options once, so the guide behaves like the Guidelime BalCon guide it is based on.
-- Nood 가이드: 발컨 가이드처럼 동작하도록 Polestar 옵션 몇 가지를 처음 한 번만 맞춥니다 (새로 추가된 옵션은 업데이트 후 한 번).
--   /nood                       다시 적용 · apply again
--   /nood undo (되돌리기)        바꾸기 전 값으로 · back to the values from before
local KO = GetLocale and GetLocale() == "koKR"
local TAG = "|cffffd200" .. "Nood" .. "|r: "

-- { Polestar setting, value, what it does }
local WANT = {
	{ "behavior.suggestFrom", KO and "nood-ko" or "nood",
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
	{ "behavior.lostQuests", "skip",
		"퀘스트를 포기하면 가이드가 그 퀘스트와 이어지는 단계를 건너뜁니다", "abandoning a quest skips it and what follows in the guide" },
}

local function ready()
	return type(Polestar) == "table" and type(Polestar.Get) == "function" and type(Polestar.Set) == "function"
end

local function apply(again)
	if not ready() then return end
	NoodGuideDB = type(NoodGuideDB) == "table" and NoodGuideDB or {}
	local db = NoodGuideDB
	db.prev = type(db.prev) == "table" and db.prev or {}
	db.done = type(db.done) == "table" and db.done or {}
	if db.applied == 1 then -- set by 1.0.5 and before: those options are done already
		for i = 1, 6 do db.done[WANT[i][1]] = true end
		db.applied = 2
	end
	local said = false
	for _, w in ipairs(WANT) do
		local path, value = w[1], w[2]
		if again or not db.done[path] then
		db.done[path] = true
		if not said then
			said = true
			print(TAG .. (KO and "Polestar 옵션을 Nood 가이드에 맞췄습니다 (되돌리기: /nood undo)" or "Polestar options set for Nood Guide (to undo: /nood undo)"))
		end
		local ok, now = pcall(Polestar.Get, path)
		if ok and now ~= value then
			if db.prev[path] == nil then db.prev[path] = { v = now } end
			pcall(Polestar.Set, path, value)
			print("  - " .. (KO and w[3] or w[4]))
		end
		end
	end
	db.applied = 2
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


---------------------------------------------------------------------------
-- 던전 카드 자동 표시: Nood 가이드의 진행 단계가 "[던전] 이름 (English)" 줄이면
-- Polestar 던전 카드("퀘스트 수집")를 명령어 없이 띄웁니다. 단계마다 한 번 (다시 접속하면 다시).
---------------------------------------------------------------------------
local told, waiting = {}, nil
-- the guide compiler writes a dungeon's name as {area:ID}; its English name for Polestar.Dungeons.Find
local AREA_EN = {
	[2437] = "Ragefire Chasm", [153] = "Ruins of Lordaeron", [718] = "Wailing Caverns", [236] = "Shadowfang Keep",
	[2797] = "Blackfathom Deeps", [17732] = "Excavation Site: Wetlands", [1717] = "Razorfen Kraul", [796] = "Scarlet Monastery",
	[1517] = "Uldaman", [978] = "Zul'Farrak", [2100] = "Maraudon", [1417] = "Sunken Temple", [1584] = "Blackrock Depths",
	[1583] = "Blackrock Spire", [2279] = "Stratholme", [722] = "Razorfen Downs",
}

local function dungeonOfStep(guide, i)
	local st = guide and guide.steps and guide.steps[i]
	if not st or not st.goals then return nil end
	for _, g in ipairs(st.goals) do
		local t = type(g) == "table" and g.text
		if type(t) == "string" then
			local en = t:match("^%[던전%][^(]-%(([^)]+)%)") or t:match("^%[Dungeon%]%s*(.-)%s+—")
			if en then
				en = en:gsub("^%s+", ""):gsub("%s+$", "")
				-- the compiler writes a place's name as {area:ID}: the game's own name for it
				en = en:gsub("{area:(%d+)}", function(id)
					if AREA_EN[tonumber(id)] then return AREA_EN[tonumber(id)] end
					local ok, name = pcall(C_Map.GetAreaInfo, tonumber(id))
					return ok and type(name) == "string" and name or ""
				end)
				if en ~= "" then return en end
			end
		end
	end
end

local function showCard(name)
	local Dg, DT = Polestar.Dungeons, Polestar.UI and Polestar.UI.DungeonToast
	if not (Dg and Dg.Find and DT and DT.Show) then return true end
	local key = Dg.Find(name)
	if not key then return true end
	local c
	for _, x in ipairs(DT.Candidates and DT.Candidates(nil, "any") or {}) do
		if x.key == key then c = x break end
	end
	if not c and Dg.Get and Dg.PickupPlan then
		local d, plan = Dg.Get(key), Dg.PickupPlan(key)
		local take = plan and plan.take and #plan.take or 0
		if not d or take == 0 then
			print(TAG .. (KO and (name .. ": 지금 받을 던전 퀘스트가 없습니다. 던전을 하셨다면 그 줄을 체크하고 넘어가세요.")
				or (name .. ": no dungeon quests to pick up now. Tick the line to move on.")))
			return true
		end
		c = { key = key, name = d.name, zoneName = d.zoneName, minLevel = d.minLevel, maxLevel = d.maxLevel,
			take = take, level = UnitLevel("player"), all = true }
	end
	return c and DT.Show(c) and true or false
end

local function checkDungeonStep()
	if not ready() then return end
	local E = Polestar.Engine
	local guide = E and E.GetGuide and E.GetGuide()
	if not guide or type(guide.id) ~= "string" or not guide.id:lower():find("nood", 1, true) then return end
	local i = E.GetLiveStep and E.GetLiveStep()
	if type(i) ~= "number" then return end
	local name = dungeonOfStep(guide, i)
	local mark = name and (guide.id .. "#" .. i)
	if not name or told[mark] then return end
	if InCombatLockdown() then waiting = true return end
	local ok, shown = pcall(showCard, name)
	if not ok or shown then told[mark] = true else waiting = true end
end

local function soon() C_Timer.After(2, checkDungeonStep) end

local f = CreateFrame("Frame")
f:RegisterEvent("PLAYER_LOGIN")
f:RegisterEvent("PLAYER_REGEN_ENABLED")
f:SetScript("OnEvent", function(_, event)
	if event == "PLAYER_LOGIN" then
		apply(false)
		if ready() and Polestar.On then
			Polestar.On("STEP_CHANGED", soon)
			Polestar.On("GUIDE_CHANGED", soon)
			Polestar.On("HEADS_UP_HIDDEN", function() if waiting then waiting = nil soon() end end)
		end
		C_Timer.After(8, checkDungeonStep)
	elseif waiting then
		waiting = nil
		soon()
	end
end)

SLASH_NOODGUIDE1 = "/nood"
SLASH_NOODGUIDE2 = "/noodguide"
SlashCmdList["NOODGUIDE"] = function(msg)
	msg = (msg or ""):lower()
	if msg:find("undo", 1, true) or msg:find("되돌리기", 1, true) then undo()
	elseif msg:find("dungeon", 1, true) or msg:find("던전", 1, true) then wipe(told) checkDungeonStep()
	else apply(true) end
end
