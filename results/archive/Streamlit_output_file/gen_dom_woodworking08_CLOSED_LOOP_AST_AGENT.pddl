(define (domain woodworking)
  (:requirements :strips :typing)

  (:types
    aboaardsize aboardsize acolour awood machine surface woodobj - object
    board part - woodobj
    glazer grinder highspeed-saw immersion-varnisher planer saw spray-varnisher - machine
  )

  (:constants
    natural - acolour
    rough smooth verysmooth - surface
    large medium small - aboardsize
    colourfragments glazed untreated varnished - object
  )

  (:predicates
    (available ?a - woodobj)
    (is-smooth ?a - surface)
    (unused ?a - woodobj)
    (varnished ?a - woodobj)
    (glazed ?a - woodobj)
    (has-colour ?a - machine ?c - acolour)
    (surface-condition ?a - woodobj ?s - surface)
    (in-highspeed-saw ?a - board ?b - highspeed-saw)
    (goalsize ?a - part ?s - object)
    (colour ?a - woodobj ?c - acolour)
    (treatment ?a - woodobj ?f - object)
    (made-of ?a - woodobj ?d - awood)
    (boardsize ?a - board ?s - object)
    (empty ?b - highspeed-saw)
    (wood ?a - woodobj ?d - awood)
    (boardsize-successor ?f - aboardsize ?g - aboardsize)
    (grind-treatment-change ?x1 - object ?x2 - object)
  )

  (:action immersion_varnish
    :parameters (?a - woodobj ?b - immersion-varnisher ?c - acolour ?d - surface)
    :precondition (and (available ?a) (has-colour ?b ?c) (surface-condition ?a ?d) (is-smooth ?d) (unused ?a))
    :effect (and (varnished ?a) (colour ?a ?c) (not (unused ?a)) (not (colour ?a natural)))
  )

  (:action spray_varnish
    :parameters (?a - woodobj ?b - spray-varnisher ?c - acolour ?d - surface)
    :precondition (and (available ?a) (has-colour ?b ?c) (surface-condition ?a ?d) (is-smooth ?d) (unused ?a))
    :effect (and (varnished ?a) (colour ?a ?c) (not (unused ?a)) (not (colour ?a natural)))
  )

  (:action glaze
    :parameters (?a - woodobj ?b - glazer ?c - acolour)
    :precondition (and (available ?a) (has-colour ?b ?c) (unused ?a))
    :effect (and (glazed ?a) (colour ?a ?c) (not (unused ?a)) (not (colour ?a natural)))
  )

  (:action grind
    :parameters (?a - woodobj ?b - grinder ?c - surface ?d - acolour ?f - object)
    :precondition (and (available ?a) (surface-condition ?a ?c) (is-smooth ?c) (colour ?a ?d) (unused ?a))
    :effect (and (surface-condition ?a verysmooth) (colour ?a natural) (not (surface-condition ?a ?c)) (not (colour ?a ?d)) (not (unused ?a)) (treatment ?a ?f))
  )

  (:action plane
    :parameters (?a - woodobj ?b - planer ?c - surface ?d - acolour)
    :precondition (and (available ?a) (surface-condition ?a ?c) (colour ?a ?d))
    :effect (and (surface-condition ?a smooth) (colour ?a natural) (not (surface-condition ?a ?c)) (not (colour ?a ?d)) (unused ?a))
  )

  (:action load_board
    :parameters (?a - board ?b - highspeed-saw)
    :precondition (and (empty ?b) (available ?a))
    :effect (and (in-highspeed-saw ?a ?b) (not (available ?a)) (not (empty ?b)))
  )

  (:action unload_board
    :parameters (?a - board ?b - highspeed-saw)
    :precondition (in-highspeed-saw ?a ?b)
    :effect (and (available ?a) (empty ?b) (not (in-highspeed-saw ?a ?b)))
  )

  (:action cut_board_small
    :parameters (?a - board ?b - part ?c - highspeed-saw ?d - awood ?e - surface ?f - aboardsize ?g - aboardsize)
    :precondition (and (unused ?b) (goalsize ?b small) (in-highspeed-saw ?a ?c) (wood ?a ?d) (surface-condition ?a ?e) (boardsize ?a ?f) (boardsize-successor ?f ?g))
    :effect (and (available ?b) (made-of ?b ?d) (surface-condition ?b ?e) (colour ?b natural) (not (unused ?b)) (boardsize ?a ?g))
  )

  (:action cut_board_medium
    :parameters (?a - board ?b - part ?c - highspeed-saw ?d - awood ?e - surface ?f - aboardsize ?g - aboardsize ?h - aboardsize)
    :precondition (and (unused ?b) (goalsize ?b medium) (in-highspeed-saw ?a ?c) (wood ?a ?d) (surface-condition ?a ?e) (boardsize ?a ?f) (boardsize-successor ?f ?g) (boardsize-successor ?g ?h))
    :effect (and (available ?b) (made-of ?b ?d) (surface-condition ?b ?e) (colour ?b natural) (not (unused ?b)) (boardsize ?a ?h))
  )

  (:action cut_board_large
    :parameters (?a - board ?b - part ?c - highspeed-saw ?d - awood ?e - surface ?f - aboardsize ?g - aboardsize ?h - aboardsize)
    :precondition (and (unused ?b) (goalsize ?b large) (in-highspeed-saw ?a ?c) (wood ?a ?d) (surface-condition ?a ?e) (boardsize ?a ?f) (boardsize-successor ?f ?g) (boardsize-successor ?g ?h))
    :effect (and (available ?b) (made-of ?b ?d) (surface-condition ?b ?e) (colour ?b natural) (not (unused ?b)) (boardsize ?a ?h))
  )

  (:action saw_board_small
    :parameters (?a - board ?b - part ?c - saw ?d - awood ?e - surface ?f - aboardsize ?g - aboardsize)
    :precondition (and (unused ?b) (goalsize ?b small) (available ?a) (wood ?a ?d) (surface-condition ?a ?e) (boardsize ?a ?f) (boardsize-successor ?f ?g))
    :effect (and (available ?b) (made-of ?b ?d) (surface-condition ?b ?e) (colour ?b natural) (not (unused ?b)) (boardsize ?a ?g))
  )

  (:action saw_board_medium
    :parameters (?a - board ?b - part ?c - saw ?d - awood ?e - surface ?f - aboardsize ?g - aboardsize ?h - aboardsize)
    :precondition (and (unused ?b) (goalsize ?b medium) (available ?a) (made-of ?a ?d) (surface-condition ?a ?e) (boardsize ?a ?f) (boardsize-successor ?f ?g) (boardsize-successor ?g ?h))
    :effect (and (available ?b) (made-of ?b ?d) (surface-condition ?b ?e) (colour ?b natural) (not (unused ?b)) (boardsize ?a ?h))
  )

  (:action saw_board_large
    :parameters (?a - board ?b - part ?c - saw ?d - awood ?e - surface ?f - aboardsize ?g - aboardsize ?h - aboardsize ?i - aboardsize)
    :precondition (and (unused ?b) (goalsize ?b large) (available ?a) (made-of ?a ?d) (surface-condition ?a ?e) (boardsize ?a ?f) (boardsize-successor ?f ?g) (boardsize-successor ?g ?h) (boardsize-successor ?h ?i))
    :effect (and (available ?b) (made-of ?b ?d) (surface-condition ?b ?e) (colour ?b natural) (not (unused ?b)) (boardsize ?a ?i))
  )

)