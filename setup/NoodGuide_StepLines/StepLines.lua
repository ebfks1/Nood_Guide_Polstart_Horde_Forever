-- Nood Guide - Step Lines (test build)
-- Copyright (C) 2026 씨가 (ebfks1). Licensed under the GNU General Public License v3.0 or later.
--
-- On the world map: a line from the current step's goal to the next step's goal, and on to the one after,
-- as many steps ahead as Polestar's own "Up next" list (and its numbered pins) shows. Straight lines between
-- the goals; Polestar itself draws the real way to the current goal.
--
-- Reads Polestar (no Polestar code is copied here):
--   Polestar.Engine.GetLiveStep / GetStepCount / GetStepView / StepNumber   the steps and their goals' places
--   Polestar.Compat.MapToWorld / WorldToMap                                 a goal's place on the map shown
--   Polestar.MapCanvas.Watch(WorldMapFrame, fn)                             a frame on the map that never writes into it
--   Polestar.Get / On                                                       the step count setting, refreshes
-- Everything is checked before use and wrapped in pcall: if Polestar changes, the lines just stop showing.

local KO = GetLocale() == "koKR"
local P = Polestar
local ADDON = ...

local DEFAULT_AHEAD = 5         -- Polestar's own fallback when "Up next" is 0
local WIDTH = 3                 -- line width on screen, pixels
local DOT = 9                   -- the mark at each goal, pixels
local FADE_TO = 0.35            -- the last line's opacity (the next one is 1)
local COLOR = { 0.2, 0.9, 1 }   -- cyan, apart from Polestar's own route line
local SHADOW = { 0, 0, 0 }

local db
local function say(msg) print("|cff33ddffNood|r: " .. msg) end

---------------------------------------------------------------------------
-- Which steps, and where
---------------------------------------------------------------------------

-- How many steps ahead: Polestar's own count for its numbered pins (0.4.0: nav.upcomingCount, 0 = as many as
-- Up next), else the guide window's Up next (ui.upcoming), else Polestar's fallback. /noodlines N overrides.
local function aheadCount()
	if db and db.count and db.count > 0 then return db.count end
	local up = P.Nav and P.Nav.upcoming
	if up and up.Count then
		local ok, n = pcall(up.Count)
		if ok and tonumber(n) and n > 0 then return n end
	end
	local n = tonumber(P.Get and P.Get("ui.upcoming")) or 0
	return n > 0 and n or DEFAULT_AHEAD
end

-- The first goal of a step that still has a place to go: { map, x, y, f, no }.
local function placeOf(E, s, live)
	local v = E.GetStepView(s, true)
	if not v or v.status == "na" or v.status == "done" or v.status == "skipped" then return nil end
	local no, hidden = s, false
	if E.StepNumber then no, hidden = E.StepNumber(s) end
	if hidden then return nil end
	for _, g in ipairs(v.goals or {}) do
		if g.map and g.x and g.y and (g.status == "active" or g.status == "pending") then
			return { map = g.map, x = g.x, y = g.y, f = g.f, no = no, live = live }
		end
	end
	return nil
end

-- The current step's place, then the next steps' (each step counts, with a place or not, as Polestar counts them).
local function chain()
	local E = P.Engine
	if not (E and E.GetLiveStep and E.GetStepCount and E.GetStepView) then return {} end
	local live = E.GetLiveStep()
	if not live then return {} end
	local out = {}
	local first = placeOf(E, live, true)
	if first then out[#out + 1] = first end
	local want, n = aheadCount(), 0
	for s = live + 1, E.GetStepCount() do
		if n >= want then break end
		local v = E.GetStepView(s, true)
		local hidden = false
		if E.StepNumber then local _; _, hidden = E.StepNumber(s) end
		if v and not hidden and v.status ~= "na" and v.status ~= "done" and v.status ~= "skipped" then
			n = n + 1
			local p = placeOf(E, s, false)
			if p then
				local last = out[#out]
				-- the same spot as the step before (one NPC for two steps): no zero-length line
				if not (last and last.map == p.map and math.abs(last.x - p.x) < 0.3 and math.abs(last.y - p.y) < 0.3) then
					out[#out + 1] = p
				end
			end
		end
	end
	return out
end

-- A place in the shown map's percent, or nil when it lies on another continent.
local function onMap(p, mapID)
	local C = P.Compat
	if not (C and C.MapToWorld and C.WorldToMap) then return nil end
	if p.map == mapID and p.f ~= "e" then return p.x, p.y end
	local c, wx, wy = C.MapToWorld(p.map, p.x, p.y, p.f)
	if not c then return nil end
	return C.WorldToMap(c, wx, wy, mapID)
end

---------------------------------------------------------------------------
-- Drawing
---------------------------------------------------------------------------

local owner              -- our frame on the map's canvas (under Polestar's view frame)
local lines, shadows, dots, labels = {}, {}, {}, {}
local used = 0
local cached, dirty = nil, true

local function hideFrom(i)
	for k = i, #lines do
		lines[k]:Hide(); shadows[k]:Hide()
	end
	for k = i, #dots do dots[k]:Hide(); labels[k]:Hide() end
end

local function makeOwner(view)
	if owner then return end
	local make = P.CreateFrameUnder
	if make then owner = make("Frame", nil, view.frame) else owner = CreateFrame("Frame", nil, view.frame) end
	owner:SetAllPoints(view.frame)
	owner:SetFrameLevel((view.frame:GetFrameLevel() or 1) + 5)
end

local function dot(i)
	if not dots[i] then
		local t = owner:CreateTexture(nil, "OVERLAY")
		t:SetTexture("Interface\\COMMON\\Indicator-Gray")
		dots[i] = t
		local fs = owner:CreateFontString(nil, "OVERLAY")
		fs:SetFont(STANDARD_TEXT_FONT, 12, "OUTLINE")
		fs:SetTextColor(1, 1, 1)
		labels[i] = fs
	end
	return dots[i], labels[i]
end

local function draw(view)
	if not (view and view.shown and view.mapID) then return end
	makeOwner(view)
	if db.off then hideFrom(1); used = 0; owner:Hide(); return end
	owner:Show()
	if dirty or not cached then
		local ok, res = pcall(chain)
		cached = ok and res or {}
		dirty = false
	end
	local w, h = view.width or owner:GetWidth(), view.height or owner:GetHeight()
	local scale = (view.scale and view.scale > 0) and view.scale or 1
	local pts = {}
	for i, p in ipairs(cached) do
		local ok, x, y = pcall(onMap, p, view.mapID)
		if ok and x and y then pts[i] = { x = x / 100 * w, y = -y / 100 * h, no = p.no, live = p.live } end
	end
	local n, total = 0, #cached
	for i = 1, total - 1 do
		local a, b = pts[i], pts[i + 1]
		if a and b then
			n = n + 1
			if not lines[n] then
				shadows[n] = owner:CreateLine(nil, "ARTWORK", nil, 1)
				lines[n] = owner:CreateLine(nil, "ARTWORK", nil, 2)
				shadows[n]:SetColorTexture(1, 1, 1, 1)
				lines[n]:SetColorTexture(1, 1, 1, 1)
			end
			local alpha = 1 - (1 - FADE_TO) * ((i - 1) / math.max(1, total - 2))
			local l, s = lines[n], shadows[n]
			s:SetVertexColor(SHADOW[1], SHADOW[2], SHADOW[3]); s:SetAlpha(alpha * 0.6)
			s:SetThickness((WIDTH + 2) / scale)
			s:SetStartPoint("TOPLEFT", owner, a.x, a.y); s:SetEndPoint("TOPLEFT", owner, b.x, b.y)
			l:SetVertexColor(COLOR[1], COLOR[2], COLOR[3]); l:SetAlpha(alpha)
			l:SetThickness(WIDTH / scale)
			l:SetStartPoint("TOPLEFT", owner, a.x, a.y); l:SetEndPoint("TOPLEFT", owner, b.x, b.y)
			l:Show(); s:Show()
		end
	end
	for k = n + 1, #lines do lines[k]:Hide(); shadows[k]:Hide() end
	used = n
	-- a small mark and the step number at each goal (the live step's has no number: Polestar marks it)
	local d = 0
	for i = 1, total do
		local p = pts[i]
		if p then
			d = d + 1
			local t, fs = dot(d)
			t:SetSize(DOT / scale, DOT / scale)
			t:ClearAllPoints(); t:SetPoint("CENTER", owner, "TOPLEFT", p.x, p.y)
			t:SetVertexColor(COLOR[1], COLOR[2], COLOR[3]); t:Show()
			if p.live or db.numbers == false then fs:Hide() else
				fs:SetFont(STANDARD_TEXT_FONT, math.max(6, 13 / scale), "OUTLINE")
				fs:SetText(tostring(p.no))
				fs:ClearAllPoints(); fs:SetPoint("BOTTOMLEFT", owner, "TOPLEFT", p.x + 4 / scale, p.y + 2 / scale)
				fs:Show()
			end
		end
	end
	for k = d + 1, #dots do dots[k]:Hide(); labels[k]:Hide() end
end

---------------------------------------------------------------------------
-- Wiring
---------------------------------------------------------------------------

local view
local function refresh()
	dirty = true
	if view and view.shown then pcall(draw, view) end
end

local pending = false
local function soon()
	if pending then return end
	pending = true
	C_Timer.After(0.2, function() pending = false; refresh() end)
end

local function start()
	if not (P and P.MapCanvas and P.MapCanvas.Watch and P.Engine) then
		say(KO and "이 Polestar 버전에서는 단계 연결선을 그릴 수 없습니다 (필요한 기능이 없음)."
			or "this Polestar cannot draw step lines (a call it needs is missing).")
		return
	end
	local ok, v = pcall(P.MapCanvas.Watch, WorldMapFrame, function(vw, what)
		if what == "show" or what == "map" or what == "size" or what == "scale" then
			if what == "show" then dirty = true end
			pcall(draw, vw)
		elseif what == "hide" then
			-- nothing: our frame goes with Polestar's view frame
		end
	end)
	if not ok or not v then
		say(KO and "세계 지도에 연결할 수 없습니다." or "could not attach to the world map.")
		return
	end
	view = v
	if P.On then
		for _, msg in ipairs({ "STEP_CHANGED", "STEP_UPDATED", "GUIDE_CHANGED", "WAYPOINT_CHANGED",
			"PLAYER_SKIPPED_STEP", "STEP_SKIPPED", "GUIDE_COMPLETED" }) do
			P.On(msg, soon)
		end
		P.On("SETTING_CHANGED", function(path)
			if path == nil or path == "" or path == "ui" or path == "nav" or path == "ui.upcoming"
				or path == "nav.upcomingCount" then soon() end
		end)
	end
end

local f = CreateFrame("Frame")
f:RegisterEvent("PLAYER_LOGIN")
f:SetScript("OnEvent", function()
	NoodStepLinesDB = NoodStepLinesDB or {}
	db = NoodStepLinesDB
	start()
end)

SLASH_NOODSTEPLINES1 = "/noodlines"
SlashCmdList.NOODSTEPLINES = function(msg)
	msg = strtrim(msg or ""):lower()
	if msg == "off" then db.off = true; refresh()
		say(KO and "단계 연결선을 껐습니다. 다시 켜기: /noodlines on" or "step lines off. /noodlines on to show them.")
	elseif msg == "on" then db.off = nil; refresh()
		say(KO and "단계 연결선을 켰습니다." or "step lines on.")
	elseif tonumber(msg) then
		local n = math.floor(tonumber(msg))
		db.count = n > 0 and n or nil; refresh()
		say(db.count and ((KO and "다음 %d단계까지 잇습니다." or "joining the next %d steps."):format(n))
			or (KO and "Polestar \"다음 단계\" 개수를 따릅니다." or "following Polestar's Up next count."))
	elseif msg == "numbers" then db.numbers = (db.numbers == false) and true or false; refresh()
	elseif msg == "debug" then
		local ok, c = pcall(chain)
		say(("steps ahead %d · places %d%s"):format(aheadCount(), ok and #c or -1, ok and "" or (" · " .. tostring(c))))
		if ok then for i, p in ipairs(c) do say(("%d: step %s map %s %.1f,%.1f %s"):format(i, tostring(p.no), tostring(p.map), p.x, p.y, p.f or "")) end end
	else
		say(KO and "/noodlines on | off | 숫자(이을 단계 수, 0 = Polestar 따름) | numbers | debug"
			or "/noodlines on | off | N (steps to join, 0 = follow Polestar) | numbers | debug")
	end
end
