# VISION — card-game-durak

> Master concept document. Single source of truth for product decisions.
> When in doubt — check here first. If a decision contradicts this file,
> either the decision is wrong, or this file must be updated (explicitly).
>
> Language: English for precision. Russian for user-facing terms where
> the original wording matters.

## 1. Product

A networked **"Podkidnoy Durak"** card game, played in a web browser.

- **Genre:** classic Russian card game, 36-card deck (6..Ace, four suits).
- **Mode:** online multiplayer, 2 to 4 players per table.
- **Players:** humans and bots, mixed freely (1 human + 3 bots, 4 humans, etc.).
- **Server:** self-hosted initially (developer's machine), later migrates to
  a cheap cloud host. Migration must be painless.
- **Client:** browser (Chrome and other modern browsers). Desktop-first,
  but architecture must allow tablet/smartphone later without rewrite.

## 2. Non-goals (explicitly out of scope)

- No mobile-native apps (iOS/Android). Browser only.
- No 3D graphics. Realistic PNG textures, not Three.js.
- No user-uploaded assets. Only curated asset packs.
- No email, no financial data, no sensitive personal data.
- No social features (friends, chat, profiles beyond nickname + stats).
- No matchmaking by skill. Manual room creation/joining only.

## 3. Core mechanics (target)

- **Deck:** 36 cards, shuffled per game.
- **Hand size:** 6 cards per player (classic Durak).
- **Trump:** determined by the bottom card of the deck after dealing.
- **Turn flow:** attack → defend → beat or take. (Rules engine — later.)
- **Win condition:** last player holding cards is "the fool" (дурак).
- **Draw pile:** players refill to 6 after each round until deck is empty.

⚠️ **Rules engine is NOT in the first milestone.** First milestone is UI +
basic mechanics (deal, show hand, play a card without validation).

## 4. Rooms & lobby

- **Room creation:** a player creates a room, sets:
  - name (searchable),
  - visibility: **private** or **public**,
  - max players: 2, 3, or 4.
- **Joining:**
  - public rooms — visible in a list, joinable by anyone;
  - private rooms — joinable by invitation (by nickname) or by room code.
- **Start:** when the required number of players is reached, the game
  starts automatically.
- **Overflow:** impossible — the room closes to new joins once full.
- **Underflow:** players wait until the required count is reached.
- **Player leaves mid-game:** the game ends as a **draw** for everyone;
  all players return to the lobby.

## 5. Accounts & persistence

- **Auth:** nickname + password. No email, no recovery, no 2FA.
- **Purpose:** identify the player to others; store per-nickname stats.
- **Persistence:** SQLite database.
  - Stored: profiles (nickname, password hash, customization choices),
    game statistics.
  - Active games: stored in DB (survive server restart).
- **Password storage:** hash (bcrypt or hashlib). Never plaintext.
  (Even minimal security — this is basic hygiene, 3 lines of code.)
- **Security level:** minimal. No sensitive data collected.

## 6. Customization

- **Per-player, client-side.** Each player sees their own table, deck back,
  avatar, music. No server sync of visual choices.
- **Asset packs only.** Curated sets (e.g., 3 tables, 3 deck backs,
  5 avatars). No uploads.
- **Avatar:** player picks their own; can also pick bot avatars;
  cannot change other humans' avatars.
- **Music:** one background track per session. Plus action sounds
  (click, move, take, win). Volume control + mute.

## 7. Visual style & assets

- **Phase 1:** SVG minimalism. Fast to iterate, no asset pipeline.
- **Phase 2:** realistic PNG textures. Migration must be painless —
  therefore an **asset abstraction layer** is required from day one.
  Code must not know whether it renders SVG or PNG.
- **Animations:** deal, card flight to table, flip, take, win/lose screen.
- **No 3D.**

## 8. Architecture principles

- **Layered:** `domain` ← `transport` ← `main` ← `static`.
  - `domain` — pure logic, no FastAPI, no WebSocket, no I/O.
    Contains: `Card`, `Deck`, `Player`, `Table`, `Game`.
  - `transport` — connection management, auth, rooms.
    Contains: `ConnectionManager`, `Room`, `RoomManager`.
  - `main` — FastAPI app, WebSocket endpoint, static mount.
  - `static` — vanilla JS/HTML client (no build step for now).
- **Domain vs. transport boundary (hybrid):**
  - `Game` (rules: deck, hands, table, whose turn) lives in `domain`.
    It knows nothing about WebSocket or connections.
  - `Room` (who is connected, who is waiting, what to broadcast)
    lives in `transport`. It wraps a `Game` but does not implement rules.
  - `Player` (domain) = a participant in a game (name, hand, status).
    A "connection" (WebSocket + login) is a separate transport concern,
    already handled by `ConnectionManager`.
  - Rationale: rules must be testable without a network; rooms are
    infrastructure. This follows the layering rule above literally.
- **Design for growth, not for "first project".**
  - Right boundaries from day one (layers, contracts, abstractions).
  - Minimal implementations behind those boundaries.
  - No premature complexity (no microservices, no Redis, no JWT yet).
- **Typed messages.** Pydantic schemas for WebSocket messages, not raw dicts.
- **Persistence behind an interface.** In-memory or SQLite — swappable.
- **Config via environment variables.** No hardcoded hosts/ports/paths.

## 9. Tech stack

- **Backend:** Python 3.11+, FastAPI, uvicorn, WebSocket.
- **Frontend:** vanilla JS + HTML (ES modules when it grows).
  React/Svelte — only if/when UI complexity demands it.
- **DB:** SQLite.
- **Testing:** pytest.
- **Quality:** ruff, mypy, pre-commit.
- **Deployment:** self-hosted → cheap cloud host (later).

## 10. Milestones (high level)

1. **Walking skeleton** — ✅ done. Domain cards, WebSocket transport,
   test client.
2. **UI + basic mechanics** — lobby, room, table, deal, show hand,
   play a card (no rules).
3. **Rules engine** — full Durak rules, win/lose, draw pile, trump.
4. **Bots** — smart bots (evaluate situation, count cards).
5. **Persistence** — SQLite, profiles, stats, active games.
6. **Customization** — asset packs, per-player visuals, music.
7. **Cloud migration** — deploy to cheap host, multiple parallel sessions.

## 11. Open questions (deferred, not blocking)

- Exact lobby UX (invitation vs. search — both?).
- Private room join mechanism (invite vs. code — both?).
- Public room discovery (list vs. search — both?).
- Invitation UX (notification vs. auto-join).
- Full-room join attempt (disabled button vs. server reject vs. spectator).
- Underflow handling (wait vs. "start now" vs. timeout).
- Number of asset packs in first version.
- Avatar details (image only vs. name/color/frame).

## 12. Working agreements

- **Language:** Russian with the user; English in code, comments,
  docstrings, commits, configs.
- **Assistant role:** mentor-architect + executor. Explains what and why.
  Proposes, user decides.
- **Discussion format:** topic map with `▶` / `✓` / `·` markers.
  One topic at a time. See `CONVENTIONS.md` §9.
- **Message format:** emoji markers (🧠 📋 📝 ❓ ✅ ⚠️ 💡).
  See `CONVENTIONS.md` §8.
- **When in doubt:** check this file first. If it contradicts a decision,
  update this file explicitly — do not silently diverge.
