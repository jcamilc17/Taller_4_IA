"""Puntos 1–3. Retroceso, consistencia de arcos y heurísticas."""
from collections import deque
from models.csp import SearchTrace, copy_domains


def backtracking_search(csp, domains=None, select_variable=None,
                        order_values=None, trace=None):
    """Punto 1: retorna {tarea: franja} o None si no hay solución.

    Entradas: csp representa el problema; domains contiene los dominios vigentes,
    reducidos por AC-3 cuando corresponde.
    csp.variables contiene los identificadores de las tareas, en orden.
    domains es {tarea: [franjas enteras]}; assignment es {tarea: franja}.
    El bloque por completar define expand(assignment).

    Tips:
    - choose(csp, assignment, domains) retorna una tarea pendiente;
      ordered(csp, x, assignment, domains) retorna sus valores en orden.
    - consistent(x, valor, assignment) retorna si el candidato es compatible
      con la asignación parcial; es el comprobador suministrado para este bloque.
    - search(nueva_asignacion) es la llamada recursiva suministrada. Recibe
      una asignación independiente y retorna una solución completa o None.
    """
    trace = trace if trace is not None else SearchTrace(False)
    domains = copy_domains(csp.domains if domains is None else domains)
    choose = select_variable or (lambda p, a, d: next(x for x in p.variables if x not in a))
    ordering = order_values or (lambda p, x, a, d: list(d[x]))

    # Registra las decisiones y los cambios de la búsqueda.
    def snapshot(assignment):
        return {x: [assignment[x]] if x in assignment else list(domains[x])
                for x in csp.variables}

    def ordered(problem, variable, assignment, current_domains):
        values = ordering(problem, variable, assignment, current_domains)
        trace.record('select', f'Elegir {variable}. Orden de valores: {values}.',
                     assignment, snapshot(assignment) if trace.enabled else domains, variable)
        return values

    def consistent(variable, value, assignment):
        current = snapshot(assignment) if trace.enabled else domains
        trace.attempt(assignment, current, variable, value)
        valid = csp.consistent(variable, value, assignment)
        if valid and trace.enabled:
            child = {**assignment, variable: value}
            trace.record('assign', f'Asignar {variable} a la franja {value}.',
                         child, snapshot(child), variable, value)
        elif not valid:
            trace.record('reject', 'El valor entra en conflicto con una tarea asignada.',
                         assignment, current, variable, value)
        return valid

    def search(assignment):
        result = expand(assignment)
        if result is None and len(assignment) < len(csp.variables):
            trace.fail(assignment, snapshot(assignment) if trace.enabled else domains)
            if assignment and trace.enabled:
                variable = next(reversed(assignment))
                parent = {x: v for x, v in assignment.items() if x != variable}
                trace.restore(parent, snapshot(parent), variable)
        return result
      
    def expand(assignment):
        # Caso base, si todas las tareas tienen franja la asignación está completa.
        if len(assignment) == len(csp.variables):
            return assignment

        # Seleccion de la siguiente tarea pendiente según la estrategia configurada.
        variable = choose(csp, assignment, domains)

        # Recorrido de las franjas candidatas en el orden definido por ordered.
        for value in ordered(csp, variable, assignment, domains):

            # Validacion del candidato, debe ser compatible con la asignación parcial.
            if consistent(variable, value, assignment):

                # Copia independiente de la asignación para esta rama de la búsqueda.
                child = dict(assignment)
                child[variable] = value

                # Llamada recursiva; si la rama encuentra solución se propaga hacia arriba.
                result = search(child)
                if result is not None:
                    return result

        # Ninguna franja funcionó para esta tarea, se retorna None para retroceder.
        return None

    return search({})


def revise(csp, x, y, domains):
    """Punto 2: revisa X→Y modificando domains[x].

    Retorna True únicamente si cambia ese dominio; False en caso contrario.

    Tips:
    - x e y son identificadores de tareas; domains[x] y domains[y] son listas.
    - csp.compatible(x, valor_x, y, valor_y) comprueba las restricciones
      entre ese par de tareas, respetando la dirección de las precedencias.
    - Si elimina elementos mientras recorre una lista, itere sobre una copia.
    """
    changed = False

    # Recorrido sobre una copia de domains[x], ya que se eliminan elementos durante la iteración.
    for value_x in list(domains[x]):

        # Validacion de soporte, debe existir al menos un valor de y compatible con value_x.
        if not any(csp.compatible(x, value_x, y, value_y) for value_y in domains[y]):

            # Eliminacion del valor sin soporte y registro del cambio en el dominio.
            domains[x].remove(value_x)
            changed = True

    # Retorno de True únicamente si se eliminó algún valor de domains[x].
    return changed

def ac3(csp, domains):
    """Punto 2: reduce domains; retorna False si detecta un dominio vacío.

    Un retorno True indica consistencia de arcos, no garantiza una solución.

    Tips:
    - Cada arco es un par (x, y) de identificadores de tareas.
      csp.neighbors[x] contiene los vecinos de x.
    - revise(csp, x, y, domains) retorna si modificó domains[x].
    """
    # Inicializacion de la cola con todos los arcos (x, y) del problema.
    queue = deque((x, y) for x in csp.variables for y in csp.neighbors[x])

    while queue:
        x, y = queue.popleft()

        # Revision del arco x -> y, solo se continúa si domains[x] cambió.
        if revise(csp, x, y, domains):

            # Validacion de consistencia, un dominio vacío indica que no hay solución.
            if not domains[x]:
                return False

            # Reencolar los arcos (z, x), ya que la reducción de x puede quitar soporte a sus vecinos.
            for z in csp.neighbors[x]:
                if z != y:
                    queue.append((z, x))

    # Retorno de True, todos los arcos son consistentes (no garantiza que exista solución).
    return True


def select_unassigned_variable(csp, assignment, domains):
    """Punto 3: retorna el identificador de la variable elegida por MRV y grado.

    Tips:
    - csp.consistent(x, valor, assignment) comprueba si un candidato es
      compatible con la asignación parcial. Los dominios deben conservarse.
    - csp.neighbors[x] contiene sus vecinos; csp.variables conserva el orden
      original para los desempates.
    """
    # Tareas pendientes, en el orden original de csp.variables
    pending = [x for x in csp.variables if x not in assignment]

    def key(x):
        # MRV: franjas del dominio vigente compatibles con la asignación parcial
        remaining = sum(1 for value in domains[x] if csp.consistent(x, value, assignment))

        # Grado: vecinos aún sin asignar (se niega para preferir el mayor)
        degree = sum(1 for y in csp.neighbors[x] if y not in assignment)

        # Desempate final por la posición original de la variable
        return (remaining, -degree, csp.variables.index(x))

    # Tarea con menor MRV, mayor grado y menor índice original
    return min(pending, key=key)
    # FIN DEL BLOQUE DEL ESTUDIANTE


def order_domain_values(csp, variable, assignment, domains):
    """Punto 3: retorna los valores compatibles ordenados por LCV.

    Retorne una lista nueva sin modificar domains y conserve el orden original
    en los empates.

    Tips:
    - Use valores de domains compatibles con assignment, tanto para los
      candidatos como para los vecinos pendientes; compruébelos con
      csp.consistent(x, valor, assignment).
    - csp.compatible(variable, valor, vecino, valor_vecino) comprueba cada par
      sin modificar los dominios.
    """
    # Candidatos: franjas del dominio vigente compatibles con la asignación parcial
    candidates = [value for value in domains[variable]
                  if csp.consistent(variable, value, assignment)]

    # Vecinos pendientes con sus valores aún compatibles con la asignación parcial
    neighbor_values = {
        y: [w for w in domains[y] if csp.consistent(y, w, assignment)]
        for y in csp.neighbors[variable] if y not in assignment
    }

    def ruled_out(value):
        # LCV: cuántos valores de los vecinos pendientes quedarían descartados con value
        return sum(1 for y, values in neighbor_values.items()
                   for w in values if not csp.compatible(variable, value, y, w))

    # sorted es estable: en empates conserva el orden original. Retorna una lista nueva
    return sorted(candidates, key=ruled_out)
    # FIN DEL BLOQUE DEL ESTUDIANTE
