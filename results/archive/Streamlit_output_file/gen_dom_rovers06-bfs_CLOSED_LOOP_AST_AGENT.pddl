(define (domain Rover)
  (:requirements :strips :typing)

  (:types
    location_site physical_entity - object
    camera lander mode objective rover store - physical_entity
    waypoint - location_site
  )

  (:predicates
    (at ?a - rover ?w - waypoint)
    (visible ?b - waypoint ?c - waypoint)
    (equipped_for_soil_analysis ?a - rover)
    (equipped_for_rock_analysis ?a - rover)
    (store_of ?b - store ?a - rover)
    (empty ?b - store)
    (full ?b - store)
    (calibrated-with ?b - camera ?a - rover)
    (on_board ?b - camera ?a - rover)
    (equipped_for_imaging ?a - rover)
    (supports ?d - camera ?e - mode)
    (available ?a - rover)
    (channel_free ?b - lander)
    (has-soil-analysis ?a - rover ?c - object)
    (has-rock-analysis ?a - rover ?c - object)
    (has-image ?a - rover ?c - object ?e - mode)
    (at_lander ?b - lander ?w - waypoint)
    (at_soil_sample ?w - waypoint)
    (at_rock_sample ?w - waypoint)
    (visible_from ?o - objective ?w - waypoint)
    (calibration_target ?b - camera ?c - objective)
    (communicated_soil_data ?c - object)
    (communicated_rock_data ?c - object)
    (communicated_image_data ?c - object ?d - mode)
    (can_traverse ?x1 - rover ?x2 - waypoint ?x3 - waypoint)
  )

  (:action navigate_rover
    :parameters (?a - rover ?b - waypoint ?c - waypoint)
    :precondition (and (visible ?b ?c) (available ?a) (at ?a ?b) (visible ?b ?c))
    :effect (and (at ?a ?c) (not (at ?a ?b)))
  )

  (:action sample_soil
    :parameters (?a - rover ?c - waypoint ?b - store)
    :precondition (and (at ?a ?c) (at_soil_sample ?c) (equipped_for_soil_analysis ?a) (store_of ?b ?a) (empty ?b))
    :effect (and (full ?b) (has-soil-analysis ?a ?c) (not (empty ?b)) (at_soil_sample ?c))
  )

  (:action sample_rock
    :parameters (?a - rover ?c - waypoint ?b - store)
    :precondition (and (at ?a ?c) (at_rock_sample ?c) (equipped_for_rock_analysis ?a) (store_of ?b ?a) (empty ?b))
    :effect (and (full ?b) (has-rock-analysis ?a ?c) (not (empty ?b)) (at_rock_sample ?c))
  )

  (:action drop_contents
    :parameters (?a - rover ?b - store)
    :precondition (and (store_of ?b ?a) (full ?b))
    :effect (and (empty ?b) (not (full ?b)))
  )

  (:action calibrate_camera
    :parameters (?a - rover ?b - camera ?c - objective ?d - waypoint)
    :precondition (and (equipped_for_imaging ?a) (on_board ?b ?a) (at ?a ?d) (visible_from ?c ?d) (calibration_target ?b ?c))
    :effect (calibrated-with ?b ?a)
  )

  (:action take_image
    :parameters (?a - rover ?b - waypoint ?c - objective ?d - mode ?e - camera)
    :precondition (and (calibrated-with ?e ?a) (on_board ?e ?a) (equipped_for_imaging ?a) (supports ?e ?d) (visible_from ?c ?b) (at ?a ?b))
    :effect (and (has-image ?a ?c ?d) (not (calibrated-with ?e ?a)))
  )

  (:action communicate_soil_data
    :parameters (?a - rover ?d - waypoint ?b - lander ?e - waypoint ?c - object)
    :precondition (and (at ?a ?d) (at_lander ?b ?e) (has-rock-analysis ?a ?c) (visible ?d ?e) (available ?a) (channel_free ?b))
    :effect (and (channel_free ?b) (communicated_soil_data ?c) (available ?a))
  )

  (:action communicate_rock_data
    :parameters (?a - rover ?d - waypoint ?b - lander ?e - waypoint ?c - object)
    :precondition (and (at ?a ?d) (at_lander ?b ?e) (has-soil-analysis ?a ?c) (visible ?d ?e) (available ?a) (channel_free ?b))
    :effect (and (channel_free ?b) (communicated_rock_data ?c) (available ?a))
  )

  (:action communicate_image_data
    :parameters (?a - rover ?e - waypoint ?b - lander ?f - waypoint ?c - object ?d - mode)
    :precondition (and (at ?a ?e) (at_lander ?b ?f) (has-image ?a ?c ?d) (visible ?e ?f) (available ?a) (channel_free ?b))
    :effect (and (channel_free ?b) (communicated_image_data ?c ?d) (available ?a))
  )

)