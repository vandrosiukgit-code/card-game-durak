# Podkidnoy Durak — Game Rules Specification

## 1. Game Overview

**Podkidnoy Durak** is a Russian card game played with a **36-card deck** by **2 to 4 players**.

The objective is **not to win tricks**. The objective is to get rid of all cards.

The player who is left holding cards after all other players have finished is the **Durak (loser)**.

These rules define a deterministic implementation suitable for a computer game or AI agent.

---

## 2. Deck

Use a standard **36-card Russian deck**.

### Ranks

From lowest to highest:

1. 6
2. 7
3. 8
4. 9
5. 10
6. Jack
7. Queen
8. King
9. Ace

### Suits

* Hearts
* Diamonds
* Clubs
* Spades

There are:

`9 ranks × 4 suits = 36 cards`

---

## 3. Number of Players

The game supports:

* Minimum: **2 players**
* Maximum: **4 players**

Players are arranged in a fixed circular order.

For example, with four players:

```text
Player 1 → Player 2 → Player 3 → Player 4 → Player 1
```

The direction of play is clockwise unless explicitly changed by the game configuration.

---

## 4. Initial Deal

The deck is shuffled.

Each player receives **6 cards**.

The remaining cards form the **draw pile** (stock).

The top card of the remaining deck is revealed and determines the **trump suit**.

The revealed trump card is normally placed under or beside the stock so that its suit remains visible.

The trump card remains part of the stock and can be drawn later.

### Example

If the revealed card is:

```text
7 of Hearts
```

then:

```text
Trump suit = Hearts
```

All Hearts are trump cards.

---

## 5. Card Strength

Cards are compared first by whether they are trump.

### Rules

* A trump card beats every non-trump card.
* A non-trump card can beat another non-trump card only if both cards have the same suit.
* Within the same suit, the higher rank beats the lower rank.
* A non-trump card can never beat a trump card.

### Example

If Hearts are trump:

```text
6♥ beats A♣
K♥ beats A♣
A♥ beats any non-trump card
```

However:

```text
A♣ beats K♣
K♣ beats Q♣
```

---

# 6. Determining the First Attacker

The first attacker is the player holding the **lowest trump card**.

If there are no special house rules, this is the lowest-ranking trump among all players' initial hands.

For example, if the trump suit is Hearts and players hold:

```text
Player 1: 9♥
Player 2: 6♥
Player 3: K♥
Player 4: no Hearts
```

then Player 2 attacks first because they hold the lowest trump:

```text
6♥
```

With two or three players, the same rule applies.

---

# 7. Attack

The attacker places one or more cards face-up on the table.

The first attacking card may be any card from the attacker's hand.

The defender must attempt to beat every attacking card.

---

## 8. Additional Attacks — "Podkidnoy"

After the defender has received attacking cards, other cards may be added to the attack.

A card may be added only if its **rank matches the rank of at least one card already on the table**.

For example, if the table contains:

```text
8♣
K♦
```

the attackers may add:

```text
8♥
8♠
K♣
K♥
```

They may **not** add:

```text
9♣
Q♦
A♠
```

because those ranks are not currently present on the table.

---

# 9. Who May Add Cards

The original attacker may add cards.

Other players may also add cards if the implementation allows multi-player podkidnoy attacks.

For a deterministic implementation, use the following rule:

**Only the current attacker may initiate the attack and add additional cards.**

The other players do not independently add cards during the same attack.

This makes the attack sequence deterministic for an AI-controlled game.

---

# 10. Maximum Number of Attacking Cards

The total number of attacking cards in one attack may never exceed:

```text
the number of cards the defender had in their hand at the beginning of the attack
```

Therefore, if the defender started the attack with:

```text
4 cards
```

the attacker may place at most:

```text
4 attacking cards
```

on the table.

The attacker may stop attacking at any time before reaching this limit.

---

# 11. Defense

The defender must beat every attacking card.

For each attacking card, the defender must place a separate card on top of it.

A defending card must be stronger than the attacking card according to the card-strength rules.

### Example

Trump = Hearts.

Attack:

```text
9♣
```

Valid defenses include:

```text
10♣
J♣
Q♣
K♣
A♣
9♥
10♥
J♥
...
```

An invalid defense would be:

```text
10♦
```

because Diamonds cannot beat Clubs unless Diamonds are trump.

---

# 12. Beating a Trump Card

A trump card can only be beaten by a **higher trump card**.

Example:

```text
Trump = Hearts

Attack: 8♥
```

Valid defenses:

```text
9♥
10♥
J♥
Q♥
K♥
A♥
```

Invalid defenses:

```text
A♣
A♦
A♠
```

---

# 13. Beating a Non-Trump Card with Trump

Any trump card beats a non-trump card.

Example:

```text
Trump = Spades
Attack = A♥
```

The defender may use:

```text
6♠
```

because every Spade is trump.

---

# 14. Multiple Attacking Cards

Each attacking card must be defended individually.

Example:

```text
Trump = Hearts

Attack:
8♣
K♦
```

The defender could respond:

```text
9♣
A♦
```

Both attacking cards are now covered.

The defender cannot use one card to cover multiple attacking cards.

---

# 15. Defender's Options

During a defense, the defender has two possible actions:

### Option A — Beat the card

The defender places a valid higher card on the attacking card.

### Option B — Take

The defender may give up defending and **take all cards currently on the table**.

When the defender takes, the entire table is added to the defender's hand.

The attack immediately ends.

---

# 16. Continuing an Attack

After the defender successfully beats all currently exposed attacking cards, the attacker may either:

1. Add another legal attacking card, or
2. End the attack.

A new attacking card must have a rank already present among **all cards currently on the table**, including both attacking and defending cards.

### Example

Initial attack:

```text
8♣
```

Defense:

```text
10♣
```

The attacker may now play:

```text
10♦
```

because rank `10` is present on the table.

---

# 17. Successful Defense

The defense is successful when:

* Every attacking card has been covered by a valid defending card.
* The attacker has no legal additional attack, or chooses not to continue.
* The defender does not take the cards.

When the defense succeeds:

1. All cards on the table are removed from the round.
2. Those cards are placed into a discard pile.
3. The defender becomes the next attacker.
4. Players draw cards from the stock to restore their hands to 6 cards.

---

# 18. Failed Defense

If the defender chooses to take, or cannot legally defend and must take:

1. All cards on the table are added to the defender's hand.
2. The table is cleared.
3. The defender does **not** become the next attacker.
4. The same attacker starts the next attack.
5. Players draw cards from the stock to restore their hands to 6 cards.

The defender therefore receives the disadvantage of having to hold all cards taken from the table.

---

# 19. Drawing Cards

After every completed attack, players replenish their hands from the stock.

The objective is to have **6 cards** whenever enough cards remain in the stock.

Cards are drawn in the following order:

1. The current attacker
2. Other players in clockwise order
3. The defender draws last

No player may draw more than necessary to reach 6 cards.

---

# 20. Important Endgame Rule

When the stock contains fewer cards than necessary, players simply take whatever cards remain.

For example:

```text
Player has 4 cards.
Stock has 2 cards.
```

The player draws the remaining 2 cards and now has 6 cards.

If the stock becomes empty, no further cards are drawn.

From that point onward, players play only with the cards remaining in their hands.

---

# 21. Empty Hand

A player may finish the game by having **zero cards** in their hand.

However, having zero cards does not necessarily mean the player immediately wins if other players still have cards and the game state requires another action.

Once the stock is empty, a player with zero cards is considered finished and takes no further turns.

---

# 22. Player Elimination

A player is eliminated from active play when:

```text
hand.size == 0
```

and the stock is empty.

The player no longer participates in attacks or defenses.

The remaining players continue playing.

---

# 23. End of Game

The game ends when only one active player remains.

That player still has cards and is the:

```text
DURAK
```

The other players have successfully gotten rid of their cards.

### Example

Final hands:

```text
Player 1: 0 cards
Player 2: 0 cards
Player 3: 0 cards
Player 4: 7 cards
```

Result:

```text
Player 4 = Durak
```

---

# 24. Two-Player Game

With two players:

```text
Attacker ↔ Defender
```

There is no third player who can add cards.

The attacker and defender alternate according to the normal successful/failed defense rules.

---

# 25. Three-Player Game

With three players, play proceeds around the circle.

Example:

```text
Player 1 → Player 2 → Player 3 → Player 1
```

If Player 1 attacks Player 2:

* Player 2 defends.
* If the defense succeeds, Player 2 becomes the next attacker.
* If Player 2 takes, Player 1 attacks again.

---

# 26. Four-Player Game

With four players:

```text
Player 1 → Player 2 → Player 3 → Player 4 → Player 1
```

The current attacker attacks the next active player in the circular order.

If that player successfully defends, they become the next attacker.

If that player takes the cards, the same attacker attacks again.

Eliminated players are skipped when determining the next active player.

---

# 27. Legal Attack Validation

An AI or game engine should consider an attack card legal only when all of the following are true:

```text
1. The card belongs to the attacker's hand.
2. The total number of attacking cards is below the maximum attack size.
3. The card's rank exists among the ranks currently present on the table.
```

For the first attack card:

```text
Any card in the attacker's hand is legal.
```

---

# 28. Legal Defense Validation

A defense card is legal only when:

```text
1. The card belongs to the defender's hand.
2. The card has not already been used in the current defense.
3. The card can legally beat the specific attacking card.
```

Card comparison:

```text
if defender.suit == attacker.suit:
    defender.rank > attacker.rank

elif defender.suit == trump_suit:
    defender beats attacker

else:
    defender cannot beat attacker
```

A trump card can only be beaten by a higher trump card.

---

# 29. State Model

A game implementation should maintain at least the following state:

```text
players
player_hands
deck
discard_pile
trump_suit
current_attacker
current_defender
attack_cards
defense_cards
active_players
game_status
```

---

# 30. Round State

During an attack, the game state should distinguish between:

```text
ATTACKING
DEFENDING
ATTACK_CONTINUE
DEFENSE_SUCCESS
DEFENDER_TAKES
ROUND_END
GAME_OVER
```

This allows an AI agent to reason about legal actions without relying on implicit state.

---

# 31. Legal Actions

At any point, the game engine should expose only actions that are legal for the current state.

Possible actions include:

```text
PLAY_ATTACK_CARD
PLAY_DEFENSE_CARD
CONTINUE_ATTACK
END_ATTACK
TAKE_CARDS
```

The exact action set may be simplified by the implementation.

---

# 32. Determinism Requirements for AI

The implementation must explicitly define:

* Player order
* Attack direction
* Trump determination
* First attacker
* Maximum attack size
* Legal attack cards
* Legal defense cards
* Drawing order
* Behavior when a defender takes
* Behavior when a defense succeeds
* Player elimination
* End-game condition

No rule should depend on human interpretation during execution.

---

# 33. Recommended Rule Constants

For implementation, use constants rather than hard-coded values:

```text
DECK_SIZE = 36
INITIAL_HAND_SIZE = 6
MAX_PLAYERS = 4
MIN_PLAYERS = 2
RANK_COUNT = 9
```

The ranks should be represented in ascending order:

```text
6, 7, 8, 9, 10, J, Q, K, A
```

---

# 34. Core Game Loop

A simplified game loop is:

```text
1. Create and shuffle 36-card deck.
2. Deal 6 cards to each player.
3. Determine trump suit.
4. Determine first attacker.
5. Determine defender.
6. Attacker plays a legal card.
7. Defender either:
   a. beats the card, or
   b. takes the cards.
8. If the defender beats all cards:
   a. attacker may add another legal card, or
   b. attacker ends the attack.
9. If defender takes:
   a. defender receives all table cards.
   b. same attacker starts the next round.
10. If defense succeeds:
    a. discard table cards.
    b. defender becomes attacker.
11. Refill hands to 6 while cards remain.
12. Remove players who have finished.
13. Repeat until only one active player remains.
14. The remaining player is the Durak.
```

---

# 35. Rule Priority

When implementing the game, the following order should be used when resolving conflicts:

1. Game-over conditions
2. Player active/inactive status
3. Current attack/defense state
4. Card legality
5. Attack-size limit
6. Trump rules
7. Draw/refill rules
8. Turn order

The implementation must never allow an illegal action merely because the action would otherwise be useful to an AI player.
