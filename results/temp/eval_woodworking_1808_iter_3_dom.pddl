(define (domain woodworking)
  (:requirements :typing)

  (:types
    aboardsize acolour apartsize awood machine surface treatmentstatus woodobj - object
    glazer grinder highspeed-saw immersion-varnisher planer saw spray-varnisher - machine
    board part - woodobj
  )

  (:constants
    rough smooth verysmooth - surface
    colourfragments glazed untreated varnished - treatmentstatus
    natural - acolour
    large medium small - apartsize
  )

  (:predicates
    (unused ?obj - object)
    (available ?obj - object)
    (surface-condition ?obj - object ?surface - object)
    (treatment ?obj - object ?treatment - object)
    (colour ?obj - object ?colour - object)
    (wood ?obj - object ?wood - object)
    (boardsize ?board - object ?size - object)
    (goalsize ?part - object ?size - object)
    (boardsize-successor ?size1 - object ?size2 - object)
    (in-highspeed-saw ?b - object ?m - object)
    (empty ?m - object)
    (has-colour ?machine - object ?colour - object)
    (contains-part ?b - object ?p - object)
    (grind-treatment-change ?old - object ?new - object)
    (is-smooth ?surface - object)
  )

  (:action do-immersion-varnish
    :parameters (?x - part ?m - immersion-varnisher ?newcolour - acolour ?surface - surface)
    :precondition (and (available ?x) (has-colour ?m ?newcolour) (surface-condition ?x ?surface) (is-smooth ?surface) (treatment ?x untreated))
    :effect (and (treatment ?x varnished) (colour ?x ?newcolour) (not (treatment ?x untreated)) (not (colour ?x natural)))
  )

  (:action do-spray-varnish
    :parameters (?x - part ?m - spray-varnisher ?newcolour - acolour ?surface - surface)
    :precondition (and (available ?x) (has-colour ?m ?newcolour) (surface-condition ?x ?surface) (is-smooth ?surface) (treatment ?x untreated))
    :effect (and (treatment ?x varnished) (colour ?x ?newcolour) (not (treatment ?x untreated)) (not (colour ?x natural)))
  )

  (:action do-glaze
    :parameters (?x - part ?m - glazer ?newcolour - acolour)
    :precondition (and (available ?x) (has-colour ?m ?newcolour) (treatment ?x untreated))
    :effect (and (treatment ?x glazed) (colour ?x ?newcolour) (not (treatment ?x untreated)) (not (colour ?x natural)))
  )

  (:action do-grind
    :parameters (?x - part ?m - grinder ?oldsurface - surface ?oldcolour - acolour ?oldtreatment - treatmentstatus ?newtreatment - treatmentstatus)
    :precondition (and (available ?x) (surface-condition ?x ?oldsurface) (is-smooth ?oldsurface) (colour ?x ?oldcolour) (treatment ?x ?oldtreatment) (grind-treatment-change ?oldtreatment ?newtreatment))
    :effect (and (surface-condition ?x verysmooth) (treatment ?x ?newtreatment) (colour ?x natural) (not (surface-condition ?x ?oldsurface)) (not (treatment ?x ?oldtreatment)) (not (colour ?x ?oldcolour)))
  )

  (:action do-plane
    :parameters (?x - part ?m - planer ?oldsurface - surface ?oldcolour - acolour ?oldtreatment - treatmentstatus)
    :precondition (and (available ?x) (surface-condition ?x ?oldsurface) (treatment ?x ?oldtreatment) (colour ?x ?oldcolour))
    :effect (and (surface-condition ?x smooth) (treatment ?x untreated) (colour ?x natural) (not (surface-condition ?x ?oldsurface)) (not (treatment ?x ?oldtreatment)) (not (colour ?x ?oldcolour)))
  )

  (:action load-highspeed-saw
    :parameters (?b - board ?m - highspeed-saw)
    :precondition (and (empty ?m) (available ?b))
    :effect (and (in-highspeed-saw ?b ?m) (not (available ?b)) (not (empty ?m)))
  )

  (:action unload-highspeed-saw
    :parameters (?b - board ?m - highspeed-saw)
    :precondition (in-highspeed-saw ?b ?m)
    :effect (and (available ?b) (empty ?m) (not (in-highspeed-saw ?b ?m)))
  )

  (:action cut-board-small
    :parameters (?b - board ?p - part ?m - highspeed-saw ?w - awood ?surface - surface ?size_before - aboardsize ?size_after - aboardsize)
    :precondition (and (unused ?p) (goalsize ?p small) (in-highspeed-saw ?b ?m) (wood ?b ?w) (surface-condition ?b ?surface) (boardsize ?b ?size_before) (boardsize-successor ?size_before ?size_after))
    :effect (and (available ?p) (wood ?p ?w) (surface-condition ?p ?surface) (colour ?p natural) (treatment ?p untreated) (boardsize ?b ?size_after) (not (boardsize ?b ?size_before)))
  )

  (:action cut-board-medium
    :parameters (?b - board ?p - part ?m - highspeed-saw ?w - awood ?surface - surface ?size_before - aboardsize ?s1 - aboardsize ?size_after - aboardsize)
    :precondition (and (unused ?p) (goalsize ?p medium) (in-highspeed-saw ?b ?m) (wood ?b ?w) (surface-condition ?b ?surface) (boardsize ?b ?size_before) (boardsize-successor ?size_before ?s1) (boardsize-successor ?s1 ?size_after))
    :effect (and (available ?p) (wood ?p ?w) (surface-condition ?p ?surface) (colour ?p natural) (treatment ?p untreated) (boardsize ?b ?size_after) (not (boardsize ?b ?size_before)))
  )

  (:action cut-board-large
    :parameters (?b - board ?p - part ?m - highspeed-saw ?w - awood ?surface - surface ?size_before - aboardsize ?s1 - aboardsize ?s2 - aboardsize ?size_after - aboardsize)
    :precondition (and (unused ?p) (goalsize ?p large) (in-highspeed-saw ?b ?m) (wood ?b ?w) (surface-condition ?b ?surface) (boardsize ?b ?size_before) (boardsize-successor ?size_before ?s1) (boardsize-successor ?s1 ?s2) (boardsize-successor ?s2 ?size_after))
    :effect (and (available ?p) (wood ?p ?w) (surface-condition ?p ?surface) (colour ?p natural) (treatment ?p untreated) (boardsize ?b ?size_after) (not (boardsize ?b ?size_before)))
  )

  (:action do-saw-small
    :parameters (?b - board ?p - part ?m - saw ?w - awood ?surface - surface ?size_before - aboardsize ?size_after - aboardsize)
    :precondition (and (unused ?p) (goalsize ?p small) (available ?b) (wood ?b ?w) (surface-condition ?b ?surface) (boardsize ?b ?size_before) (boardsize-successor ?size_before ?size_after))
    :effect (and (available ?p) (wood ?p ?w) (surface-condition ?p ?surface) (colour ?p natural) (treatment ?p untreated) (boardsize ?b ?size_after) (not (boardsize ?b ?size_before)))
  )

  (:action do-saw-medium
    :parameters (?b - board ?p - part ?m - saw ?w - awood ?surface - surface ?size_before - aboardsize ?s1 - aboardsize ?size_after - aboardsize)
    :precondition (and (unused ?p) (goalsize ?p medium) (available ?b) (wood ?b ?w) (surface-condition ?b ?surface) (boardsize ?b ?size_before) (boardsize-successor ?size_before ?s1) (boardsize-successor ?s1 ?size_after))
    :effect (and (available ?p) (wood ?p ?w) (surface-condition ?p ?surface) (colour ?p natural) (treatment ?p untreated) (boardsize ?b ?size_after) (not (boardsize ?b ?size_before)))
  )

  (:action do-saw-large
    :parameters (?b - board ?p - part ?m - saw ?w - awood ?surface - surface ?size_before - aboardsize ?s1 - aboardsize ?s2 - aboardsize ?size_after - aboardsize)
    :precondition (and (unused ?p) (goalsize ?p large) (available ?b) (wood ?b ?w) (surface-condition ?b ?surface) (boardsize ?b ?size_before) (boardsize-successor ?size_before ?s1) (boardsize-successor ?s1 ?s2) (boardsize-successor ?s2 ?size_after))
    :effect (and (available ?p) (wood ?p ?w) (surface-condition ?p ?surface) (colour ?p natural) (treatment ?p untreated) (boardsize ?b ?size_after) (not (boardsize ?b ?size_before)))
  )

)