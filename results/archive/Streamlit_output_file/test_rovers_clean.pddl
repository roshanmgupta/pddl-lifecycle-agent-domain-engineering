(define (domain Rover)
  (:requirements :strips :typing)

  (:types
    camera lander mode objective rover store waypoint - object
  )

  (:predicates
    (visible ?arg1 - waypoint ?arg2 - waypoint)
    (at_soil_sample ?arg1 - waypoint)
    (at_rock_sample ?arg1 - waypoint)
    (at_lander ?arg1 - lander ?arg2 - waypoint)
    (channel_free ?arg1 - lander)
    (at ?arg1 - rover ?arg2 - waypoint)
    (available ?arg1 - rover)
    (store_of ?arg1 - store ?arg2 - rover)
    (empty ?arg1 - store)
    (equipped_for_soil_analysis ?arg1 - rover)
    (equipped_for_rock_analysis ?arg1 - rover)
    (equipped_for_imaging ?arg1 - rover)
    (can_traverse ?arg1 - rover ?arg2 - waypoint ?arg3 - waypoint)
    (on_board ?arg1 - camera ?arg2 - rover)
    (calibration_target ?arg1 - camera ?arg2 - objective)
    (supports ?arg1 - camera ?arg2 - mode)
    (visible_from ?arg1 - objective ?arg2 - waypoint)
    (communicated_soil_data ?arg1 - waypoint)
    (communicated_rock_data ?arg1 - waypoint)
    (communicated_image_data ?arg1 - objective ?arg2 - mode)
    (full ?b - store)
    (has_soil_analysis ?a - rover ?c - waypoint)
    (has_rock_analysis ?a - rover ?c - waypoint)
    (calibrated_to ?b - camera ?a - rover)
    (has_image ?a - rover ?c - objective ?e - mode)
  )

  (:action navigate_rover
    :parameters (?a - rover ?src - waypoint ?dst - waypoint)
    :precondition (and (can_traverse ?a ?src ?dst) (available ?a) (at ?a ?src) (visible ?src ?dst))
    :effect (and (at ?a ?dst) (not (at ?a ?src)))
  )

  (:action sample_soil
    :parameters (?a - rover ?c - waypoint ?b - store)
    :precondition (and (at ?a ?c) (at_soil_sample ?c) (equipped_for_soil_analysis ?a) (store_of ?b ?a) (empty ?b))
    :effect (and (not (empty ?b)) (at_soil_sample ?c) (full ?b) (has_soil_analysis ?a ?c))
  )

  (:action sample_rock
    :parameters (?a - rover ?c - waypoint ?b - store)
    :precondition (and (at ?a ?c) (at_rock_sample ?c) (equipped_for_rock_analysis ?a) (store_of ?b ?a) (empty ?b))
    :effect (and (not (empty ?b)) (at_rock_sample ?c) (full ?b) (has_rock_analysis ?a ?c))
  )

  (:action drop_contents
    :parameters (?a - rover ?b - store)
    :precondition (and (store_of ?b ?a) (full ?b))
    :effect (and (empty ?b) (not (full ?b)))
  )

  (:action calibrate_rover
    :parameters (?a - rover ?b - camera ?c - objective ?d - waypoint)
    :precondition (and (equipped_for_imaging ?a) (calibration_target ?b ?c) (at ?a ?d) (visible_from ?c ?d) (on_board ?b ?a))
    :effect (calibrated_to ?b ?a)
  )

  (:action take_image
    :parameters (?a - rover ?b - waypoint ?c - objective ?d - camera ?e - mode)
    :precondition (and (calibrated_to ?d ?a) (on_board ?d ?a) (equipped_for_imaging ?a) (supports ?d ?e) (visible_from ?c ?b) (at ?a ?b))
    :effect (and (has_image ?a ?c ?e) (not (calibrated_to ?d ?a)))
  )

  (:action communicate_soil_data
    :parameters (?a - rover ?d - waypoint ?b - lander ?e - waypoint ?c - waypoint)
    :precondition (and (at ?a ?d) (at_lander ?b ?e) (has_soil_analysis ?a ?c) (visible ?d ?e) (available ?a) (channel_free ?b))
    :effect (and (channel_free ?b) (communicated_soil_data ?c) (available ?a))
  )

  (:action communicate_rock_data
    :parameters (?a - rover ?d - waypoint ?b - lander ?e - waypoint ?c - waypoint)
    :precondition (and (at ?a ?d) (at_lander ?b ?e) (has_rock_analysis ?a ?c) (visible ?d ?e) (available ?a) (channel_free ?b))
    :effect (and (channel_free ?b) (communicated_rock_data ?c) (available ?a))
  )

  (:action communicate_image_data
    :parameters (?a - rover ?e - waypoint ?b - lander ?f - waypoint ?c - objective ?d - mode)
    :precondition (and (at ?a ?e) (at_lander ?b ?f) (has_image ?a ?c ?d) (visible ?e ?f) (available ?a) (channel_free ?b))
    :effect (and (channel_free ?b) (communicated_image_data ?c ?d) (available ?a))
  )

)