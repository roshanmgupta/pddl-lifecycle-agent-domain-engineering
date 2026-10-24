(define (domain Rover)
  (:requirements :strips :typing)

  (:types
    physical_entity - object
    camera lander mobile_unit mode objective store waypoint - physical_entity
    rover - mobile_unit
  )

  (:constants
    calibration_target store_of - object
  )

  (:predicates
    (at ?x - physical_entity ?y - waypoint)
    (on_board ?x - camera ?y - mobile_unit)
    (visible ?x - waypoint ?y - waypoint)
    (empty ?s - store)
    (full ?s - store)
    (calibrated-to ?c - camera ?m - mobile_unit)
    (equipped_for_soil_analysis ?m - mobile_unit)
    (equipped_for_rock_analysis ?m - mobile_unit)
    (equipped_for_imaging ?m - mobile_unit)
    (available ?m - mobile_unit)
    (can_traverse ?m - mobile_unit ?from - waypoint ?to - waypoint)
    (supports ?c - camera ?mode - mode)
    (channel_free ?l - lander)
    (has-soil-analysis ?m - mobile_unit ?data - physical_entity)
    (has-rock-analysis ?m - mobile_unit ?data - physical_entity)
    (has-image ?m - mobile_unit ?data - objective ?mode - mode)
    (communicated_soil_data ?w - waypoint)
    (communicated_rock_data ?w - waypoint)
    (communicated_image_data ?o - objective ?mode - mode)
    (at_soil_sample ?w - waypoint)
    (at_rock_sample ?w - waypoint)
    (at_lander ?l - lander ?w - waypoint)
    (visible_from ?o - objective ?w - waypoint)
    (store_of ?s - store ?m - mobile_unit)
    (calibration_target ?c - camera ?o - objective)
  )

  (:action navigate
    :parameters (?m - mobile_unit ?from - waypoint ?to - waypoint)
    :precondition (and (can_traverse ?m ?from ?to) (available ?m) (at ?m ?from) (visible ?from ?to))
    :effect (and (at ?m ?to) (not (at ?m ?from)))
  )

  (:action sample-soil
    :parameters (?m - mobile_unit ?c - waypoint ?s - store)
    :precondition (and (at ?m ?c) (at_soil_sample ?c) (equipped_for_soil_analysis ?m) (empty ?s) (store_of ?s ?m))
    :effect (and (full ?s) (has-soil-analysis ?m ?c) (not (empty ?s)) (not (at_soil_sample ?c)))
  )

  (:action sample-rock
    :parameters (?m - mobile_unit ?c - waypoint ?s - store)
    :precondition (and (at ?m ?c) (at_rock_sample ?c) (equipped_for_rock_analysis ?m) (empty ?s) (store_of ?s ?m))
    :effect (and (full ?s) (has-rock-analysis ?m ?c) (not (empty ?s)) (not (at_rock_sample ?c)))
  )

  (:action drop-contents
    :parameters (?m - mobile_unit ?s - store)
    :precondition (and (full ?s) (store_of ?s ?m))
    :effect (and (empty ?s) (not (full ?s)))
  )

  (:action calibrate
    :parameters (?m - mobile_unit ?c - camera ?o - objective ?w - waypoint)
    :precondition (and (equipped_for_imaging ?m) (at ?m ?w) (visible_from ?o ?w) (on_board ?c ?m) (calibration_target ?c ?o))
    :effect (calibrated-to ?c ?m)
  )

  (:action take-image
    :parameters (?m - mobile_unit ?w - waypoint ?o - objective ?c - camera ?mode - mode)
    :precondition (and (calibrated-to ?c ?m) (on_board ?c ?m) (equipped_for_imaging ?m) (supports ?c ?mode) (visible_from ?o ?w) (at ?m ?w))
    :effect (and (has-image ?m ?o ?mode) (not (calibrated-to ?c ?m)))
  )

  (:action communicate-soil-data
    :parameters (?m - mobile_unit ?d - waypoint ?l - lander ?e - waypoint ?c - objective)
    :precondition (and (at ?m ?d) (at_lander ?l ?e) (has-soil-analysis ?m ?c) (visible ?d ?e) (available ?m) (channel_free ?l))
    :effect (and (channel_free ?l)  (available ?m) (communicated_soil_data ?d))
  )

  (:action communicate-rock-data
    :parameters (?m - mobile_unit ?d - waypoint ?l - lander ?e - waypoint ?c - objective)
    :precondition (and (at ?m ?d) (at_lander ?l ?e) (has-rock-analysis ?m ?c) (visible ?d ?e) (available ?m) (channel_free ?l))
    :effect (and (channel_free ?l) (has-rock-analysis ?c) (available ?m) (communicated_rock_data ?d))
  )

  (:action communicate-image-data
    :parameters (?m - mobile_unit ?e - waypoint ?l - lander ?f - waypoint ?o - objective ?c - camera ?mode - mode)
    :precondition (and (at ?m ?e) (at_lander ?l ?f) (has-image ?m ?o ?mode) (visible ?e ?f) (available ?m) (channel_free ?l))
    :effect (and (channel_free ?l) (has-image ?o ?mode) (available ?m) (communicated_image_data ?o ?mode))
  )

)