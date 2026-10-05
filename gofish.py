#!/usr/bin/env python3
"""gofish —— 终端钓鱼纸牌 (Go Fish): 你 vs 电脑。纯标准库。"""

import argparse
import random
import secrets
import sys
from collections import Counter

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["♠", "♥", "♦", "♣"]
NAMES = ["你", "电脑"]


def card_name(card):
    r, s = card
    return f"{r}{s}"


def new_deck():
    """52 张不重复的牌。"""
    return [(r, s) for r in RANKS for s in SUITS]


def check_books(hand):
    """检查手牌中的成书(4 张同点): 就地移除并返回新增书数。"""
    cnt = Counter(r for r, _ in hand)
    made = sum(1 for c in cnt.values() if c == 4)
    hand[:] = [c for c in hand if cnt[c[0]] != 4]
    return made


def hand_ranks(hand):
    return sorted({r for r, _ in hand}, key=RANKS.index)


def ai_choose_rank(hand, rng):
    """简单 AI 策略: 问自己手里张数最多的点数, 并列时随机。
    (诚实说明: 这是最朴素的启发式, 不记牌、不推理, 会被会记牌的人类玩家针对。)"""
    cnt = Counter(r for r, _ in hand)
    best = max(cnt.values())
    cands = [r for r, c in cnt.items() if c == best]
    return rng.choice(cands)


def ask(asker, opponent, rank):
    """asker 向 opponent 索要 rank。
    返回 (ok, 张数): ok=True 表示对方有该点数, 全部交出。"""
    got = [c for c in opponent if c[0] == rank]
    if got:
        opponent[:] = [c for c in opponent if c[0] != rank]
        asker.extend(got)
        return True, len(got)
    return False, 0


class Game:
    def __init__(self, rng):
        self.rng = rng
        self.deck = new_deck()
        rng.shuffle(self.deck)
        self.hands = [[self.deck.pop() for _ in range(7)] for _ in range(2)]
        self.books = [0, 0]
        for i in range(2):
            self.books[i] += check_books(self.hands[i])
        self.turn = 0  # 0=你, 1=电脑

    def total_books(self):
        return self.books[0] + self.books[1]

    def ensure_hand(self, who):
        # 手牌空了且牌堆还有牌: 摸一张续命(简化规则)
        if not self.hands[who] and self.deck:
            self.hands[who].append(self.deck.pop())

    def play_turn(self, choose_rank):
        """进行一回合。choose_rank(hand, rng) -> rank。
        索要成功或摸到所要的牌则继续, 否则换边。返回回合日志。"""
        me, opp = self.turn, 1 - self.turn
        self.ensure_hand(me)
        if not self.hands[me]:
            self.turn = opp
            return f"{NAMES[me]} 无牌可出, 跳过。"
        rank = choose_rank(self.hands[me], self.rng)
        ok, n = ask(self.hands[me], self.hands[opp], rank)
        if ok:
            self.books[me] += check_books(self.hands[me])
            return f"{NAMES[me]} 问 {rank}: 对方交出 {n} 张, 继续!"
        # Go Fish
        if self.deck:
            drawn = self.deck.pop()
            self.hands[me].append(drawn)
            self.books[me] += check_books(self.hands[me])
            if drawn[0] == rank:
                return (f"{NAMES[me]} 问 {rank}: 对方没有, 摸到 {card_name(drawn)}"
                        " 正好是要的点数, 继续!")
            self.turn = opp
            return f"{NAMES[me]} 问 {rank}: 对方没有, Go Fish! 轮到{NAMES[opp]}。"
        self.turn = opp
        return f"{NAMES[me]} 问 {rank}: 对方没有, 牌堆已空, 轮到{NAMES[opp]}。"

    def finished(self):
        return self.total_books() >= 13

    def winner(self):
        if self.books[0] > self.books[1]:
            return 0
        if self.books[1] > self.books[0]:
            return 1
        return -1


def render_hand(hand):
    return " ".join(card_name(c) for c in sorted(hand, key=lambda c: (RANKS.index(c[0]), c[1])))


def play_interactive(seed):
    rng = random.Random(seed) if seed is not None else random.Random(secrets.randbits(64))
    g = Game(rng)
    print("=== Go Fish 钓鱼纸牌 ===")
    print("规则: 每轮问对方要一个你手里有的点数; 对方有就全部交出(你继续),")
    print("      没有就 Go Fish 摸一张, 摸到所要的点数也可以继续。")
    print("集齐 4 张同点即成书得 1 分, 共 13 本, 多者胜。输入 quit 退出。\n")
    while not g.finished():
        me = g.turn
        print(f"--- {NAMES[me]} 的回合 (书: 你 {g.books[0]} : {g.books[1]} 电脑, 牌堆 {len(g.deck)} 张) ---")
        if me == 0:
            print("你的手牌:", render_hand(g.hands[0]))
            while True:
                s = input("问电脑要什么点数? (如 7 / J / Q, quit 退出): ").strip()
                if s.lower() in ("quit", "exit", "退出"):
                    print("已退出。")
                    return 0
                s = s.upper()
                if s in RANKS and s in hand_ranks(g.hands[0]):
                    print(g.play_turn(lambda h, r: s))
                    break
                print("请输入你手里有的点数。")
        else:
            print(f"电脑手牌: {len(g.hands[1])} 张")
            print(g.play_turn(ai_choose_rank))
    w = g.winner()
    print(f"\n终局! 书: 你 {g.books[0]} : {g.books[1]} 电脑")
    print("🎉 你赢了!" if w == 0 else "电脑赢了。" if w == 1 else "平局!")
    return 0


def play_auto(seed):
    rng = random.Random(seed) if seed is not None else random.Random(secrets.randbits(64))
    g = Game(rng)
    rounds = 0
    while not g.finished() and rounds < 100000:
        g.play_turn(ai_choose_rank)
        rounds += 1
    w = g.winner()
    who = "先手(AI-0)" if w == 0 else "后手(AI-1)" if w == 1 else "平局"
    print(f"AI 对战结束: 书 {g.books[0]} : {g.books[1]}, {rounds} 回合, {who}胜出")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Go Fish 钓鱼纸牌: 你 vs 电脑 (纯标准库)")
    ap.add_argument("--auto", action="store_true", help="AI vs AI 快速演示")
    ap.add_argument("--seed", type=int, default=None, help="随机种子(可复现)")
    args = ap.parse_args(argv)
    if args.auto:
        return play_auto(args.seed)
    if not sys.stdin.isatty():
        print("error: 交互模式需要终端; 管道/脚本请用 --auto", file=sys.stderr)
        return 2
    return play_interactive(args.seed)


if __name__ == "__main__":
    raise SystemExit(main())
