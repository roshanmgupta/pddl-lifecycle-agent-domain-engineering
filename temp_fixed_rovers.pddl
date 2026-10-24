(define (domain Rover)
  (:requirements :strips :typing)

  (:types
    rover - mobile_unit
    location_site physical_entity - object
    camera lander mobile_unit mode objective store - physical_entity
    waypoint - location_site
  )

  (:predicates
    (at ?x - mobile_unit ?y - waypoint)
    (at_lander ?x - lander ?y - waypoint)
    (visible ?x - waypoint ?y - waypoint)
    (empty ?s - store)
    (full ?s - store)
    (calibrated-to ?c - camera ?m - mobile_unit)
    (equipped_for_soil_analysis ?r - mobile_unit)
    (equipped_for_rock_analysis ?r - mobile_unit)
    (equipped_for_imaging ?r - mobile_unit)
    (supports ?c - camera ?m - mode)
    (has-soil-analysis ?r - mobile_unit ?s - waypoint)
    (has-rock-analysis ?r - mobile_unit ?s - waypoint)
    (has-image ?r - mobile_unit ?o - objective ?m - mode)
    (available ?r - mobile_unit)
    (channel_free ?l - lander)
    (calibration_target ?c - camera ?o - objective)
    (visible_from ?o - objective ?w - waypoint)
    (at_soil_sample ?w - waypoint)
    (at_rock_sample ?w - waypoint)
    (communicated_soil_data ?w - waypoint)
    (communicated_rock_data ?w - waypoint)
    (communicated_image_data ?o - objective ?m - mode)
    (can_traverse ?r - mobile_unit ?src - waypoint ?dst - waypoint)
    (on_board ?c - camera ?r - mobile_unit)
    (store_of ?x1 - store ?x2 - rover)
  )

  (:action navigate_rover
    :parameters (?r - mobile_unit ?src - waypoint ?dst - waypoint)
    :precondition (and (can_traverse ?r ?src ?dst) (available ?r) (at ?r ?src) (visible ?src ?dst))
    :effect (and (at ?r ?dst) (not (at ?r ?src)))
  )

  (:action sample_soil
    :parameters (?r - mobile_unit ?w - waypoint ?s - store)
    :precondition (and (at ?r ?w) (at_soil_sample ?w) (equipped_for_soil_analysis ?r) (empty ?s))
    :effect (and (full ?s) (has-soil-analysis ?r ?w) (not (empty ?s)))
  )

  (:action sample_rock
    :parameters (?r - mobile_unit ?w - waypoint ?s - store)
    :precondition (and (at ?r ?w) (at_rock_sample ?w) (equipped_for_rock_analysis ?r) (empty ?s))
    :effect (and (full ?s) (has-rock-analysis ?r ?w) (not (empty ?s)))
  )

  (:action drop_contents
    :parameters (?r - mobile_unit ?s - store)
    :precondition (full ?s)
    :effect (and (empty ?s) (not (full ?s)))
  )

  (:action calibrate_rover
    :parameters (?r - mobile_unit ?c - camera ?o - objective ?w - waypoint)
    :precondition (and (equipped_for_imaging ?r) (calibration_target ?c ?o) (at ?r ?w) (visible_from ?o ?w) (on_board ?c ?r))
    :effect (calibrated-to ?c ?r)
  )

  (:action take_image
    :parameters (?r - mobile_unit ?w - waypoint ?o - objective ?c - camera ?m - mode)
    :precondition (and (calibrated-to ?c ?r) (on_board ?c ?r) (equipped_for_imaging ?r) (supports ?c ?m) (visible_from ?o ?w) (at ?r ?w))
    :effect (and (has-image ?r ?o ?m) (not (calibrated-to ?c ?r)))
  )

  (:action communicate_soil_data
    :parameters (?r - mobile_unit ?d - waypoint ?l - lander ?e - waypoint ?s - waypoint)
    :precondition (and (at ?r ?d) (at_lander ?l ?e) (has-soil-analysis ?r ?s) (visible ?d ?e) (available ?r) (channel_free ?l))
    :effect (and (channel_free ?l) (has-soil-analysis ?r ?s) (available ?r) (communicated_soil_data ?s))
  )

  (:action communicate_rock_data
    :parameters (?r - mobile_unit ?d - waypoint ?l - lander ?e - waypoint ?s - waypoint)
    :precondition (and (at ?r ?d) (at_lander ?l ?e) (has-rock-analysis ?r ?s) (visible ?d ?e) (available ?r) (channel_free ?l))
    :effect (and (channel_free ?l) (has-rock-analysis ?r ?s) (available ?r) (communicated_rock_data ?s))
  )

  (:action communicate_image_data
    :parameters (?r - mobile_unit ?e - waypoint ?l - lander ?f - waypoint ?o - objective ?c - camera ?m - mode)
    :precondition (and (at ?r ?e) (at_lander ?l ?f) (has-image ?r ?o ?m) (visible ?e ?f) (available ?r) (channel_free ?l))
    :effect (and (channel_free ?l) (has-image ?r ?o ?m) (available ?r) (communicated_image_data ?o ?m))
  )

)