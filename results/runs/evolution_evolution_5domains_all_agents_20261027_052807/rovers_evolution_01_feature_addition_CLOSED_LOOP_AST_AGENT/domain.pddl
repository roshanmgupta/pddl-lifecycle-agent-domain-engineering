(define (domain Rover)
  (:requirements :strips :typing)

  (:types
    rover store waypoint - object
    lander - rover
  )

  (:predicates
    (at ?x - rover ?y - waypoint)
    (can_traverse ?r - rover ?x - waypoint ?y - waypoint)
    (equipped_for_rock_analysis ?r - rover)
    (empty ?s - store)
    (have_rock_analysis ?r - rover ?w - waypoint)
    (full ?s - store)
    (available ?r - rover)
    (visible ?w - waypoint ?p - waypoint)
    (communicated_rock_data ?w - waypoint)
    (at_rock_sample ?w - waypoint)
    (store_of ?s - store ?r - rover)
  )

  (:action navigate
    :parameters (?x - rover ?y - waypoint ?z - waypoint)
    :precondition (and (can_traverse ?x ?y ?z) (available ?x) (at ?x ?y) (visible ?y ?z))
    :effect (and (not (at ?x ?y)) (at ?x ?z) (available ?x))
  )

  (:action sample_rock
    :parameters (?x - rover ?s - store ?p - waypoint)
    :precondition (and (at ?x ?p) (at_rock_sample ?p) (equipped_for_rock_analysis ?x) (store_of ?s ?x) (empty ?s))
    :effect (and (not (empty ?s)) (full ?s) (have_rock_analysis ?x ?p) (at_rock_sample ?p))
  )

  (:action drop
    :parameters (?x - rover ?y - store)
    :precondition (and (store_of ?y ?x) (full ?y))
    :effect (and (not (full ?y)) (empty ?y))
  )

  (:action communicate_rock_data
    :parameters (?r - rover ?p - waypoint ?w - waypoint)
    :precondition (and (at ?r ?w) (have_rock_analysis ?r ?p) (available ?r))
    :effect (and (communicated_rock_data ?p) (available ?r))
  )

  (:action communicate_rock_data_orbitally
    :parameters (?r - rover ?p - waypoint ?w - waypoint)
    :precondition (and (at ?r ?w) (have_rock_analysis ?r ?p) (available ?r))
    :effect (communicated_rock_data ?p)
  )

)