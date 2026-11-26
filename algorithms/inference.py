"""Punto 5. Inferencia mediante encadenamiento hacia adelante."""
from models.logic import match_premises, substitute


def forward_chain(kb):
    """Retorna una tupla con los hechos originales y derivados, sin duplicados.

    Cada ronda usa los hechos disponibles al comenzarla. La base de entrada
    debe conservarse.
    kb.facts contiene objetos Atom; kb.rules contiene objetos Rule con los
    atributos premises y conclusion. Los hechos se comparan directamente.

    Tips:
    - match_premises(regla.premises, hechos) genera (sustitución, hechos usados).
      Si no hay coincidencias, no genera resultados. La sustitución es un
      diccionario, por ejemplo {'?p': 'ana'}.
    - substitute(regla.conclusion, sustitución) retorna un nuevo objeto Atom
      con las variables reemplazadas por los valores de la sustitución.
    """
    known = list(kb.facts)
    seen = set(known)
    changed = True

    while changed:
        round_facts = tuple(known)
        new_facts = []
        for rule in kb.rules:
            for substitution, _ in match_premises(rule.premises, round_facts):
                conclusion = substitute(rule.conclusion, substitution)
                if conclusion not in seen:
                    seen.add(conclusion)
                    new_facts.append(conclusion)
        known.extend(new_facts)
        changed = bool(new_facts)

    return tuple(known)
