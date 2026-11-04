(define (domain woodworking)
  (:requirements :strips :typing)

  (:types
    aboardsize acolour apartsize awood machine surface treatmentstatus woodobj - object
    board part - woodobj
    glazer grinder highspeed-saw immersion-varnisher planer saw spray-varnisher - machine
  )

  (:constants
    natural - acolour
    rough smooth verysmooth - surface
    colourfragments glazed untreated varnished - treatmentstatus
    large medium small - aboardsize
  )

  (:predicates
    (available ?a - woodobj)
    (is-smooth ?s - surface)
    (unused ?a - part)
    (varnished ?a - woodobj)
    (glazed ?a - woodobj)
    (has-colour ?a - object ?c - acolour)
    (surface-condition ?a - woodobj ?s - surface)
    (in-highspeed-saw ?a - board ?b - highspeed-saw)
    (empty ?b - highspeed-saw)
    (goalsize ?a - part ?s - aboardsize)
    (made-of ?a - woodobj ?w - awood)
    (treatment ?a - woodobj ?t - object)
    (very-smooth ?s - surface)
    (natural ?c - acolour)
    (smooth ?s - surface)
    (colour ?a - woodobj ?c - acolour)
    (wood ?a - woodobj ?w - awood)
    (boardsize ?a - board ?s - aboardsize)
    (equal ?e - treatmentstatus ?f - treatmentstatus)
    (boardsize-successor ?f - aboardsize ?g - aboardsize)
    (has-surface ?b - woodobj ?e - surface)
    (size ?b - woodobj ?x2 - aboardsize)
    (color ?b - part ?x2 - acolour)
    (has-treatment ?b - part ?x2 - treatmentstatus)
    (grind-treatment-change ?x1 - treatmentstatus ?x2 - treatmentstatus)
  )

  (:action immersion-varnish
    :parameters (?a - part ?b - immersion-varnisher ?c - acolour ?d - surface)
    :precondition (and (available ?a) (has-colour ?b ?c) (surface-condition ?a ?d) (is-smooth ?d) (unused ?a))
    :effect (and (varnished ?a) (has-colour ?a ?c) (not (unused ?a)) (not (has-colour ?a natural)))
  )

  (:action spray-varnish
    :parameters (?a - part ?b - spray-varnisher ?c - acolour ?d - surface)
    :precondition (and (available ?a) (has-colour ?b ?c) (surface-condition ?a ?d) (is-smooth ?d) (unused ?a))
    :effect (and (varnished ?a) (has-colour ?a ?c) (not (unused ?a)) (not (has-colour ?a natural)))
  )

  (:action glaze
    :parameters (?a - part ?b - glazer ?c - acolour)
    :precondition (and (available ?a) (has-colour ?b ?c) (unused ?a))
    :effect (and (glazed ?a) (has-colour ?a ?c) (not (unused ?a)) (not (has-colour ?a natural)))
  )

  (:action grind
    :parameters (?a - part ?b - grinder ?c - surface ?d - acolour ?e - treatmentstatus ?f - treatmentstatus)
    :precondition (and (available ?a) (surface-condition ?a ?c) (is-smooth ?c) (colour ?a ?d) (treatment ?a ?e))
    :effect (and (surface-condition ?a verysmooth) (colour ?a natural) (treatment ?a ?f) (not (surface-condition ?a ?c)) (not (treatment ?a ?e)) (not (colour ?a ?d)))
  )

  (:action plane
    :parameters (?a - part ?b - planer ?c - surface ?d - acolour ?e - object)
    :precondition (and (available ?a) (surface-condition ?a ?c) (treatment ?a ?e) (colour ?a ?d))
    :effect (and (surface-condition ?a smooth) (colour ?a natural) (treatment ?a untreated) (not (surface-condition ?a ?c)) (not (treatment ?a ?e)) (not (colour ?a ?d)))
  )

  (:action load-board
    :parameters (?a - board ?b - highspeed-saw)
    :precondition (and (empty ?b) (available ?a))
    :effect (and (in-highspeed-saw ?a ?b) (not (available ?a)) (not (empty ?b)))
  )

  (:action unload-board
    :parameters (?a - board ?b - highspeed-saw)
    :precondition (in-highspeed-saw ?a ?b)
    :effect (and (available ?a) (empty ?b) (not (in-highspeed-saw ?a ?b)))
  )

  (:action cut-board-small
    :parameters (?a - board ?b - part ?c - highspeed-saw ?d - awood ?e - surface ?f - aboardsize ?g - aboardsize)
    :precondition (and (unused ?b) (goalsize ?b small) (in-highspeed-saw ?a ?c) (wood ?a ?d) (surface-condition ?a ?e) (boardsize ?a ?f) (boardsize-successor ?f ?g))
    :effect (and (available ?b) (made-of ?b ?d) (has-surface ?b ?e) (colour ?b natural) (treatment ?b untreated) (boardsize ?a ?g) (not (unused ?b)))
  )

  (:action cut-board-medium
    :parameters (?a - board ?b - part ?c - highspeed-saw ?d - awood ?e - surface ?f - aboardsize ?g - aboardsize ?h - aboardsize)
    :precondition (and (unused ?b) (goalsize ?b medium) (in-highspeed-saw ?a ?c) (wood ?a ?d) (surface-condition ?a ?e) (boardsize ?a ?f) (boardsize-successor ?f ?g) (boardsize-successor ?g ?h))
    :effect (and (available ?b) (made-of ?b ?d) (has-surface ?b ?e) (colour ?b natural) (treatment ?b untreated) (boardsize ?a ?h) (not (unused ?b)))
  )

  (:action cut-board-large
    :parameters (?a - board ?b - part ?c - highspeed-saw ?d - awood ?e - surface ?f - aboardsize ?g - aboardsize ?h - aboardsize)
    :precondition (and (unused ?b) (goalsize ?b large) (in-highspeed-saw ?a ?c) (wood ?a ?d) (surface-condition ?a ?e) (boardsize ?a ?f) (boardsize-successor ?f ?g) (boardsize-successor ?g ?h))
    :effect (and (available ?b) (made-of ?b ?d) (has-surface ?b ?e) (colour ?b natural) (treatment ?b untreated) (boardsize ?a ?h) (not (unused ?b)))
  )

  (:action saw-board-small
    :parameters (?a - board ?b - part ?c - saw ?d - awood ?e - surface ?f - aboardsize ?g - aboardsize)
    :precondition (and (unused ?b) (goalsize ?b small) (available ?a) (wood ?a ?d) (surface-condition ?a ?e) (boardsize ?a ?f) (boardsize-successor ?f ?g))
    :effect (and (available ?b) (made-of ?b ?d) (has-surface ?b ?e) (colour ?b natural) (treatment ?b untreated) (boardsize ?a ?g) (not (unused ?b)))
  )

  (:action saw-board-medium
    :parameters (?a - board ?b - part ?c - saw ?d - awood ?e - surface ?f - aboardsize ?g - aboardsize ?h - aboardsize)
    :precondition (and (unused ?b) (size ?b medium) (available ?a) (made-of ?a ?d) (has-surface ?a ?e) (size ?a ?f) (boardsize-successor ?f ?g) (boardsize-successor ?g ?h))
    :effect (and (available ?b) (made-of ?b ?d) (has-surface ?b ?e) (color ?b natural) (has-treatment ?b untreated) (size ?a ?h) (not (unused ?b)))
  )

  (:action saw-board-large
    :parameters (?a - board ?b - part ?c - saw ?d - awood ?e - surface ?f - aboardsize ?g - aboardsize ?h - aboardsize)
    :precondition (and (unused ?b) (size ?b large) (available ?a) (made-of ?a ?d) (has-surface ?a ?e) (size ?a ?f) (boardsize-successor ?f ?g) (boardsize-successor ?g ?h))
    :effect (and (available ?b) (made-of ?b ?d) (has-surface ?b ?e) (color ?b natural) (has-treatment ?b untreated) (size ?a ?h) (not (unused ?b)))
  )

)