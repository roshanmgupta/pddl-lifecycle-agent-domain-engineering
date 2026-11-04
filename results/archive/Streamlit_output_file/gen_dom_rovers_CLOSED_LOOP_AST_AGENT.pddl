(define (domain Rover)
  (:requirements :strips :typing)

  (:types
    location_site physical_entity - object
    camera lander mode objective rover store - physical_entity
    waypoint - location_site
  )

  (:predicates
    (at ?a - rover ?w - waypoint)
    (visible ?w1 - waypoint ?w2 - waypoint)
    (can_traverse ?a - rover ?w1 - waypoint ?w2 - waypoint)
    (available ?a - rover)
    (equipped_for_soil_analysis ?a - rover)
    (equipped_for_rock_analysis ?a - rover)
    (empty ?s - store)
    (full ?s - store)
    (calibration_target ?c - camera ?o - objective)
    (supports ?c - camera ?m - mode)
    (has-soil-analysis ?a - rover ?c - waypoint)
    (has-rock-analysis ?a - rover ?c - waypoint)
    (has-image ?a - rover ?c - objective ?m - mode)
    (channel_free ?l - lander)
    (at_lander ?l - lander ?w - object)
    (visible_from ?o - objective ?w - waypoint)
    (communicated_soil_data ?c - waypoint)
    (communicated_rock_data ?c - waypoint)
    (communicated_image_data ?c - objective ?m - mode)
    (at_soil_sample ?c - waypoint)
    (at_rock_sample ?c - waypoint)
    (equipped_for_imaging ?a - rover)
    (on_board ?c - camera ?a - rover)
    (calibrated-to ?c - camera ?a - rover)
    (store_of ?x1 - store ?x2 - rover)
  )

  (:action navigate_rover
    :parameters (?a - rover ?src - waypoint ?dst - waypoint)
    :precondition (and (can_traverse ?a ?src ?dst) (available ?a) (at ?a ?src) (visible ?src ?dst))
    :effect (and (at ?a ?dst) (not (at ?a ?src)))
  )

  (:action sample_soil
    :parameters (?a - rover ?c - waypoint ?s - store)
    :precondition (and (at ?a ?c) (equipped_for_soil_analysis ?a) (empty ?s))
    :effect (and (full ?s) (not (empty ?s)) (not (at_soil_sample ?c)))
  )

  (:action sample_rock
    :parameters (?a - rover ?c - waypoint ?s - store)
    :precondition (and (at ?a ?c) (equipped_for_rock_analysis ?a) (empty ?s))
    :effect (and (full ?s) (not (empty ?s)) (not (at_rock_sample ?c)))
  )

  (:action drop_contents
    :parameters (?s - store)
    :precondition (full ?s)
    :effect (and (empty ?s) (not (full ?s)))
  )

  (:action calibrate_rover
    :parameters (?a - rover ?c - camera ?o - objective ?w - waypoint)
    :precondition (and (equipped_for_imaging ?a) (calibration_target ?c ?o) (at ?a ?w) (visible_from ?o ?w) (on_board ?c ?a))
    :effect (calibrated-to ?c ?a)
  )

  (:action take_image
    :parameters (?a - rover ?w - waypoint ?c - objective ?d - camera ?m - mode)
    :precondition (and (calibrated-to ?d ?a) (on_board ?d ?a) (equipped_for_imaging ?a) (supports ?d ?m) (visible_from ?c ?w) (at ?a ?w))
    :effect (and (has-image ?a ?c ?m) (not (calibrated-to ?d ?a)))
  )

  (:action communicate_soil_data
    :parameters (?a - rover ?d - waypoint ?l - lander ?at_lander_e - waypoint)
    :precondition (and (at ?a ?d) (at_lander ?l ?at_lander_e) (visible ?d ?at_lander_e) (available ?a) (channel_free ?l))
    :effect (and (channel_free ?l) (communicated_soil_data ?d))
  )

  (:action communicate_rock_data
    :parameters (?a - rover ?d - waypoint ?l - lander ?at_lander_e - waypoint)
    :precondition (and (at ?a ?d) (at_lander ?l ?at_lander_e) (available ?a) (channel_free ?l))
    :effect (and (channel_free ?l) (communicated_rock_data ?d))
  )

  (:action communicate_image_data
    :parameters (?a - rover ?e - waypoint ?l - lander ?c - objective ?m - mode ?f - object)
    :precondition (and (at ?a ?e) (at_lander ?l ?f) (has-image ?a ?c ?m) (visible_from ?c ?e) (available ?a) (channel_free ?l))
    :effect (and (channel_free ?l) (communicated_image_data ?c ?m))
  )

)