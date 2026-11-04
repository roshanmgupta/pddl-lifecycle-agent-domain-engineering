(define (domain pegsolitaire-sequential)
  (:requirements :strips :typing)

  (:types
    location - object
  )

  (:predicates
    (IN-LINE ?x - object ?y - object ?z - object)
    (occupied ?l - object)
    (free ?l - object)
    (move-ended)
    (last-visited ?l - object)
  )

  (:action jump-new-move
    :parameters (?from - location ?over - location ?to - location)
    :precondition (and (move-ended) (IN-LINE ?from ?over ?to) (occupied ?from) (occupied ?over) (free ?to))
    :effect (and (not (move-ended)) (not (occupied ?from)) (not (occupied ?over)) (not (free ?to)) (free ?from) (free ?over) (occupied ?to) (last-visited ?to))
  )

  (:action jump-continue-move
    :parameters (?from - location ?over - location ?to - location)
    :precondition (and (last-visited ?from) (IN-LINE ?from ?over ?to) (occupied ?from) (occupied ?over) (free ?to))
    :effect (and (not (occupied ?from)) (not (occupied ?over)) (not (free ?to)) (free ?from) (free ?over) (occupied ?to) (not (last-visited ?from)) (last-visited ?to))
  )

  (:action end-move
    :parameters (?loc - location)
    :precondition (last-visited ?loc)
    :effect (and (move-ended) (not (last-visited ?loc)))
  )

)