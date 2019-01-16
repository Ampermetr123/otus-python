#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------
# Реализуйте функцию best_hand, которая принимает на вход
# покерную "руку" (hand) из 7ми карт и возвращает лучшую
# (относительно значения, возвращаемого hand_rank)
# "руку" из 5ти карт. У каждой карты есть масть(suit) и
# ранг(rank)
# Масти: трефы(clubs, C), пики(spades, S), червы(hearts, H), бубны(diamonds, D)
# Ранги: 2, 3, 4, 5, 6, 7, 8, 9, 10 (ten, T), валет (jack, J), дама (queen, Q), король (king, K), туз (ace, A)
# Например: AS - туз пик (ace of spades), TH - дестяка черв (ten of hearts), 3C - тройка треф (three of clubs)

# Задание со *
# Реализуйте функцию best_wild_hand, которая принимает на вход
# покерную "руку" (hand) из 7ми карт и возвращает лучшую
# (относительно значения, возвращаемого hand_rank)
# "руку" из 5ти карт. Кроме прочего в данном варианте "рука"
# может включать джокера. Джокеры могут заменить карту любой
# масти и ранга того же цвета, в колоде два джокерва.
# Черный джокер '?B' может быть использован в качестве треф
# или пик любого ранга, красный джокер '?R' - в качестве черв и бубен
# любого ранга.

# Одна функция уже реализована, сигнатуры и описания других даны.
# Вам наверняка пригодится itertools
# Можно свободно определять свои функции и т.п.
# -----------------

import itertools
from functools import reduce


def hand_rank(hand):
    """Возвращает значение определяющее ранг 'руки'"""
    ranks = card_ranks(hand)
    if straight(ranks) and flush(hand):
        return (8, max(ranks))
    elif kind(4, ranks):
        return (7, kind(4, ranks), kind(1, ranks))
    elif kind(3, ranks) and kind(2, ranks):
        return (6, kind(3, ranks), kind(2, ranks))
    elif flush(hand):
        return (5, ranks)
    elif straight(ranks):
        return (4, max(ranks))
    elif kind(3, ranks):
        return (3, kind(3, ranks), ranks)
    elif two_pair(ranks):
        return (2, two_pair(ranks), ranks)
    elif kind(2, ranks):
        return (1, kind(2, ranks), ranks)
    else:
        return (0, ranks)


def card_ranks(hand):
    """Возвращает список рангов (его числовой эквивалент),
    отсортированный от большего к меньшему"""
    translate_map = {value: index for index, value in enumerate('0123456789TJQKA')}
    return sorted([translate_map[card[0]] for card in hand], reverse=True)


def flush(hand):
    """Возвращает True, если все карты одной масти"""
    return reduce(lambda x, y: x if x[1] == y[1] else '__', hand) == hand[0]


def straight(ranks):
    """Возвращает True, если отсортированные ранги формируют последовательность 5ти,
    где у 5ти карт ранги идут по порядку (стрит)"""
    seq_counter = 0
    for i in range(len(ranks) - 1):
        if ranks[i] - ranks[i + 1] == 1:
            seq_counter += 1
    return seq_counter >= len(ranks) - 1


def kind(n, ranks):
    """Возвращает первый ранг, который n раз встречается в данной руке.
    Возвращает None, если ничего не найдено"""
    for r in ranks:
        if ranks.count(r) == n:
            return r
    return None


def two_pair(ranks):
    """Если есть две пары, то возврщает два соответствующих ранга,
    иначе возвращает None"""
    pairs_list = ([r[0] for r in itertools.combinations(ranks, 2) if r.count(r[0]) == 2])
    if len(pairs_list) > 1:
        pairs_list.sort(reverse=True)
        return pairs_list[0], pairs_list[1]
    return None


def best_hand(hand):
    """Из "руки" в 7 карт возвращает лучшую "руку" в 5 карт """
    return best_rank_and_hand(hand)[1]


def best_rank_and_hand(hand):
    """Из "руки" в 7 карт возвращает лучшую (ранг, руку) в 5 карт """
    hands5_combinations = ((hand_rank(h), h) for h in itertools.combinations(hand, 5))
    return reduce(lambda h1, h2: h1 if h1 > h2 else h2, hands5_combinations)


def best_ranks_and_hands_of_six(hand, deck):
    """К руке из 6 карт добавляет карту из колоды и возвращается для неё лучшую (ранг, руку) из 5 карт """
    for card in deck:
        yield best_rank_and_hand(itertools.chain([card], hand))


def best_ranks_and_hands_of_five(hand, deck1, deck2):
    """К руке из 5 карт добавляет по 2 карты из колод и возвращает для неё лучшую (ранг, руку) из 5 карт """
    for (card1, card2) in itertools.product(deck1, deck2):
        yield best_rank_and_hand(itertools.chain([card1, card2], hand))


def best_wild_hand(hand):
    """best_hand но с джокерами"""
    black_cards = (x + y for y in 'CS' for x in '23456789TJQKA')
    red_cards = (m + n for n in 'HD' for m in '23456789TJQKA')
    if '?R' in hand and '?B' in hand:
        hand.remove('?R')
        hand.remove('?B')
        return reduce(lambda h1, h2: h1 if h1 > h2 else h2,
                      best_ranks_and_hands_of_five(hand, black_cards, red_cards))[1]
    elif '?R' in hand:
        hand.remove('?R')
        return reduce(lambda h1, h2: h1 if h1 > h2 else h2,
                      best_ranks_and_hands_of_six(hand, red_cards))[1]
    elif '?B' in hand:
        hand.remove('?B')
        return reduce(lambda h1, h2: h1 if h1 > h2 else h2,
                      best_ranks_and_hands_of_six(hand, black_cards))[1]
    else:
        return best_hand(hand)


def test_best_hand():
    print("test_best_hand...")
    assert (sorted(best_hand("6C 7C 8C 9C TC 5C JS".split()))
            == ['6C', '7C', '8C', '9C', 'TC'])
    assert (sorted(best_hand("TD TC TH 7C 7D 8C 8S".split()))
            == ['8C', '8S', 'TC', 'TD', 'TH'])
    assert (sorted(best_hand("JD TC TH 7C 7D 7S 7H".split()))
            == ['7C', '7D', '7H', '7S', 'JD'])
    print('OK')


# noinspection PyPep8,PyPep8,PyPep8
def test_best_wild_hand():
    print("test_best_wild_hand...")
    assert (sorted(best_wild_hand("6C 7C 8C 9C TC 5C ?B".split()))
            == ['7C', '8C', '9C', 'JC', 'TC'])
    # noinspection PyPep8
    assert (sorted(best_wild_hand("TD TC 5H 5C 7C ?R ?B".split()))
            == ['7C', 'TC', 'TD', 'TH', 'TS'])
    assert (sorted(best_wild_hand("JD TC TH 7C 7D 7S 7H".split()))
            == ['7C', '7D', '7H', '7S', 'JD'])
    print('OK')


if __name__ == '__main__':
    test_best_hand()
    test_best_wild_hand()
