(define (domain woodworking08)
  (:requirements :strips :typing)

  (:types
    aboardsize acolour apartsize awood machine surface treatmentstatus woodobj - object
    glazer grinder highspeed-saw immersion-varnisher planer saw spray-varnisher - machine
    board part - woodobj
  )

  (:constants
    glazed untreated varnished - treatmentstatus
    rough smooth verysmooth - surface
    natural - acolour
    large medium small - aboardsize
  )

  (:predicates
    (has-colour ?x - object ?y - acolour)
    (has-wood ?x - woodobj ?y - awood)
    (has-surface ?x - woodobj ?y - object)
    (is-available ?x - woodobj)
    (is-unused ?x - part)
    (is-in ?x - woodobj ?y - highspeed-saw)
    (is-empty ?x - highspeed-saw)
    (is-undergoing ?x - woodobj ?y - object)
    (is-successor ?x - object ?y - object)
  )

  (:action immersion-varnish
    :parameters (?a - part ?b - immersion-varnisher ?c - acolour ?d - surface)
    :precondition (and (is-available ?a) (has-colour ?b ?c) (has-surface ?a ?d) (is-undergoing ?a untreated) (is-successor ?d smooth))
    :effect (and (is-undergoing ?a varnished) (not (is-undergoing ?a untreated)) (not (has-colour ?a natural)) (has-colour ?a ?c))
  )

  (:action spray-varnish
    :parameters (?a - part ?b - spray-varnisher ?c - acolour ?d - surface)
    :precondition (and (is-available ?a) (has-colour ?b ?c) (has-surface ?a ?d) (is-undergoing ?a untreated) (is-successor ?d smooth))
    :effect (and (is-undergoing ?a varnished) (not (is-undergoing ?a untreated)) (not (has-colour ?a natural)) (has-colour ?a ?c))
  )

  (:action glaze
    :parameters (?a - part ?b - glazer ?c - acolour)
    :precondition (and (is-available ?a) (has-colour ?b ?c) (is-undergoing ?a untreated))
    :effect (and (is-undergoing ?a glazed) (not (is-undergoing ?a untreated)) (not (has-colour ?a natural)) (has-colour ?a ?c))
  )

  (:action grind
    :parameters (?a - part ?b - grinder ?c - surface ?d - acolour ?e - treatmentstatus ?f - treatmentstatus)
    :precondition (and (is-available ?a) (has-surface ?a ?c) (is-successor ?c smooth) (has-colour ?a ?d) (is-undergoing ?a ?e) (is-successor ?e ?f))
    :effect (and (has-surface ?a verysmooth) (is-undergoing ?a ?f) (has-colour ?a natural) (not (has-surface ?a ?c)) (not (is-undergoing ?a ?e)) (not (has-colour ?a ?d)))
  )

  (:action plane
    :parameters (?a - part ?b - planer ?c - surface ?d - acolour ?e - object)
    :precondition (and (is-available ?a) (has-surface ?a ?c) (is-undergoing ?a untreated) (has-colour ?a ?d))
    :effect (and (has-surface ?a smooth) (is-undergoing ?a untreated) (has-colour ?a natural) (not (has-surface ?a ?c)) (not (is-undergoing ?a ?e)) (not (has-colour ?a ?d)))
  )

  (:action load-board
    :parameters (?a - board ?b - highspeed-saw)
    :precondition (and (is-empty ?b) (is-available ?a))
    :effect (and (is-in ?a ?b) (not (is-available ?a)) (not (is-empty ?b)))
  )

  (:action unload-board
    :parameters (?a - board ?b - highspeed-saw)
    :precondition (is-in ?a ?b)
    :effect (and (is-available ?a) (is-empty ?b) (not (is-in ?a ?b)))
  )

  (:action cut-small
    :parameters (?a - board ?b - part ?c - highspeed-saw ?d - awood ?e - surface ?f - aboardsize ?g - aboardsize)
    :precondition (and (is-unused ?b) (is-successor ?g small) (is-in ?a ?c) (has-wood ?a ?d) (has-surface ?a ?e) (is-successor ?f ?g))
    :effect (and (is-available ?b) (has-wood ?b ?d) (has-surface ?b ?e) (has-colour ?b natural) (is-undergoing ?b untreated) (is-successor ?f ?g))
  )

  (:action cut-medium
    :parameters (?a - board ?b - part ?c - highspeed-saw ?d - awood ?e - surface ?f - aboardsize ?g - aboardsize ?h - aboardsize)
    :precondition (and (is-unused ?b) (is-successor ?g medium) (is-in ?a ?c) (has-wood ?a ?d) (has-surface ?a ?e) (is-successor ?f ?g) (is-successor ?g ?h))
    :effect (and (is-available ?b) (has-wood ?b ?d) (has-surface ?b ?e) (has-colour ?b natural) (is-undergoing ?b untreated) (is-successor ?f ?h))
  )

  (:action cut-large
    :parameters (?a - board ?b - part ?c - highspeed-saw ?d - awood ?e - surface ?f - aboardsize ?g - aboardsize ?h - aboardsize ?i - aboardsize)
    :precondition (and (is-unused ?b) (is-successor ?g large) (is-in ?a ?c) (has-wood ?a ?d) (has-surface ?a ?e) (is-successor ?f ?g) (is-successor ?g ?h) (is-successor ?h ?i))
    :effect (and (is-available ?b) (has-wood ?b ?d) (has-surface ?b ?e) (has-colour ?b natural) (is-undergoing ?b untreated) (is-successor ?f ?i))
  )

  (:action saw-small
    :parameters (?a - board ?b - part ?c - saw ?d - awood ?e - surface ?f - aboardsize ?g - aboardsize)
    :precondition (and (is-unused ?b) (is-successor ?g small) (is-available ?a) (has-wood ?a ?d) (has-surface ?a ?e) (is-successor ?f ?g))
    :effect (and (is-available ?b) (has-wood ?b ?d) (has-surface ?b ?e) (has-colour ?b natural) (is-undergoing ?b untreated) (is-successor ?f ?g))
  )

  (:action saw-medium
    :parameters (?a - board ?b - part ?c - saw ?d - awood ?e - surface ?f - aboardsize ?g - aboardsize ?h - aboardsize)
    :precondition (and (is-unused ?b) (is-successor ?g medium) (is-available ?a) (has-wood ?a ?d) (has-surface ?a ?e) (is-successor ?f ?g) (is-successor ?g ?h))
    :effect (and (is-available ?b) (has-wood ?b ?d) (has-surface ?b ?e) (has-colour ?b natural) (is-undergoing ?b untreated) (is-successor ?f ?h))
  )

  (:action saw-large
    :parameters (?a - board ?b - part ?c - saw ?d - awood ?e - surface ?f - aboardsize ?g - aboardsize ?h - aboardsize ?i - aboardsize)
    :precondition (and (is-unused ?b) (is-successor ?g large) (is-available ?a) (has-wood ?a ?d) (has-surface ?a ?e) (is-successor ?f ?g) (is-successor ?g ?h) (is-successor ?h ?i))
    :effect (and (is-available ?b) (has-wood ?b ?d) (has-surface ?b ?e) (has-colour ?b natural) (is-undergoing ?b untreated) (is-successor ?f ?i))
  )

)