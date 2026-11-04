(define (domain Rover)
  (:requirements :strips :typing)

  (:types
    camera lander mode objective rover store waypoint - object
  )

  (:predicates
    (at ?x - object ?y - object)
    (at_lander ?x - object ?y - object)
    (can_traverse ?r - object ?x - object ?y - object)
    (equipped_for_soil_analysis ?r - object)
    (equipped_for_rock_analysis ?r - object)
    (equipped_for_imaging ?r - object)
    (empty ?s - object)
    (have_rock_analysis ?r - object ?w - object)
    (have_soil_analysis ?r - object ?w - object)
    (full ?s - object)
    (calibrated ?c - object ?r - object)
    (supports ?c - object ?m - object)
    (available ?r - object)
    (visible ?w - object ?p - object)
    (have_image ?r - object ?o - object ?m - object)
    (communicated_soil_data ?w - object)
    (communicated_rock_data ?w - object)
    (communicated_image_data ?o - object ?m - object)
    (at_soil_sample ?w - object)
    (at_rock_sample ?w - object)
    (visible_from ?o - object ?w - object)
    (store_of ?s - object ?r - object)
    (calibration_target ?i - object ?o - object)
    (on_board ?i - object ?r - object)
    (channel_free ?l - object)
  )

  (:action navigate
    :parameters (?x - rover ?y - waypoint ?z - waypoint)
    :precondition (and (can_traverse ?x ?y ?z) (available ?x) (at ?x ?y) (visible ?y ?z))
    :effect (and (at ?x ?z) (not (at ?x ?y)))
  )

  (:action sample_soil
    :parameters (?x - rover ?s - store ?p - waypoint)
    :precondition (and (at ?x ?p) (at_soil_sample ?p) (equipped_for_soil_analysis ?x) (store_of ?s ?x) (empty ?s))
    :effect (and (full ?s) (have_soil_analysis ?x ?p) (not (empty ?s)) (not (at_soil_sample ?p)))
  )

  (:action sample_rock
    :parameters (?x - rover ?s - store ?p - waypoint)
    :precondition (and (at ?x ?p) (at_rock_sample ?p) (equipped_for_rock_analysis ?x) (store_of ?s ?x) (empty ?s))
    :effect (and (full ?s) (have_rock_analysis ?x ?p) (not (empty ?s)) (not (at_rock_sample ?p)))
  )

  (:action drop
    :parameters (?x - rover ?y - store)
    :precondition (and (store_of ?y ?x) (full ?y))
    :effect (and (empty ?y) (not (full ?y)))
  )

  (:action calibrate
    :parameters (?r - rover ?i - camera ?t - objective ?w - waypoint)
    :precondition (and (equipped_for_imaging ?r) (calibration_target ?i ?t) (at ?r ?w) (visible_from ?t ?w) (on_board ?i ?r))
    :effect (calibrated ?i ?r)
  )

  (:action take_image
    :parameters (?r - rover ?p - waypoint ?o - objective ?i - camera ?m - mode)
    :precondition (and (calibrated ?i ?r) (on_board ?i ?r) (equipped_for_imaging ?r) (supports ?i ?m) (visible_from ?o ?p) (at ?r ?p))
    :effect (and (have_image ?r ?o ?m) (not (calibrated ?i ?r)))
  )

  (:action communicate_soil_data
    :parameters (?r - rover ?l - lander ?p - waypoint ?x - waypoint ?y - waypoint)
    :precondition (and (at ?r ?p) (at_lander ?l ?y) (have_soil_analysis ?r ?x) (visible ?p ?y) (available ?r) (channel_free ?l))
    :effect (and (available ?r) (channel_free ?l) (communicated_soil_data ?x))
  )

  (:action communicate_rock_data
    :parameters (?r - rover ?l - lander ?p - waypoint ?x - waypoint ?y - waypoint)
    :precondition (and (at ?r ?p) (at_lander ?l ?y) (have_rock_analysis ?r ?x) (visible ?p ?y) (available ?r) (channel_free ?l))
    :effect (and (available ?r) (channel_free ?l) (communicated_rock_data ?x))
  )

  (:action communicate_image_data
    :parameters (?r - rover ?l - lander ?o - objective ?m - mode ?x - waypoint ?y - waypoint)
    :precondition (and (at ?r ?x) (at_lander ?l ?y) (have_image ?r ?o ?m) (visible ?x ?y) (available ?r) (channel_free ?l))
    :effect (and (available ?r) (channel_free ?l) (communicated_image_data ?o ?m))
  )

)