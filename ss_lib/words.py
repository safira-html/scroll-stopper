"""Helpers puros para listas de palavras com tempo ([{w, s, e}])."""

MIN_WORD_S = 0.02


def enforce_monotonic(words: list, min_dur: float = MIN_WORD_S) -> list:
    """Garante s < e, s >= fim da anterior e nenhuma sobreposicao, ja no arredondamento de 2 casas.

    Escolha: quando uma palavra nao tem espaco, ela e empurrada para frente (a proxima palavra
    ouvida pode ganhar um inicio um pouco mais tarde, em centesimos de segundo); nunca recua nem
    reordena. Devolve uma lista nova.
    """
    out, prev_end = [], 0.0
    for w in words:
        start = max(round(w["s"], 2), prev_end)
        end = max(round(w["e"], 2), round(start + min_dur, 2))
        out.append({**w, "s": start, "e": end})
        prev_end = end
    return out
