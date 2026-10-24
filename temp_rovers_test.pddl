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
    (visible ?x - waypoint ?y - waypoint)
    (at_soil_sample ?x - waypoint)
    (at_rock_sample ?x - waypoint)
    (available ?x - mobile_unit)
    (empty ?x - store)
    (full ?x - store)
    (equipped_for_soil_analysis ?x - mobile_unit)
    (equipped_for_rock_analysis ?x - mobile_unit)
    (equipped_for_imaging ?x - mobile_unit)
    (calibrated-to ?x - camera ?y - mobile_unit)
    (on_board ?x - camera ?y - mobile_unit)
    (supports ?x - camera ?y - mode)
    (has-soil-analysis ?x - mobile_unit ?y - waypoint)
    (has-rock-analysis ?x - mobile_unit ?y - waypoint)
    (has-image ?x - mobile_unit ?y - objective ?z - mode)
    (channel_free ?x - lander)
    (store_of ?x - store ?y - mobile_unit)
    (calibration_target ?x - camera ?y - objective)
    (at_lander ?x - lander ?y - waypoint)
    (visible_from ?x - objective ?y - waypoint)
    (communicated_soil_data ?x - waypoint)
    (communicated_rock_data ?x - waypoint)
    (communicated_image_data ?x - objective ?y - mode)
    (can_traverse ?rover - mobile_unit ?from - waypoint ?to - waypoint)
  )

  (:action navigate_rover
    :parameters (?rover - mobile_unit ?from - waypoint ?to - waypoint)
    :precondition (and (at ?rover ?from) (available ?rover) (visible ?from ?to) (can_traverse ?rover ?from ?to))
    :effect (and (at ?rover ?to) (not (at ?rover ?from)))
  )

  (:action sample_soil
    :parameters (?rover - mobile_unit ?waypoint - waypoint ?store - store)
    :precondition (and (at ?rover ?waypoint) (at_soil_sample ?waypoint) (equipped_for_soil_analysis ?rover) (store_of ?store ?rover) (empty ?store))
    :effect (and (full ?store) (has-soil-analysis ?rover ?waypoint) (not (empty ?store)))
  )

  (:action sample_rock
    :parameters (?rover - mobile_unit ?waypoint - waypoint ?store - store)
    :precondition (and (at ?rover ?waypoint) (at_rock_sample ?waypoint) (equipped_for_rock_analysis ?rover) (store_of ?store ?rover) (empty ?store))
    :effect (and (full ?store) (has-rock-analysis ?rover ?waypoint) (not (empty ?store)))
  )

  (:action drop_contents
    :parameters (?rover - mobile_unit ?store - store)
    :precondition (and (store_of ?store ?rover) (full ?store))
    :effect (and (empty ?store) (not (full ?store)))
  )

  (:action calibrate_rover
    :parameters (?rover - mobile_unit ?camera - camera ?objective - objective ?waypoint - waypoint)
    :precondition (and (equipped_for_imaging ?rover) (on_board ?camera ?rover) (calibration_target ?camera ?objective) (at ?rover ?waypoint) (visible_from ?objective ?waypoint))
    :effect (calibrated-to ?camera ?rover)
  )

  (:action take_image
    :parameters (?rover - mobile_unit ?waypoint - waypoint ?objective - objective ?camera - camera ?mode - mode)
    :precondition (and (calibrated-to ?camera ?rover) (on_board ?camera ?rover) (equipped_for_imaging ?rover) (supports ?camera ?mode) (visible_from ?objective ?waypoint) (at ?rover ?waypoint))
    :effect (has-image ?rover ?objective ?mode)
  )

  (:action communicate_soil_data
    :parameters (?rover - mobile_unit ?lander - lander ?waypoint_data - waypoint ?waypoint - waypoint ?lander_loc - waypoint)
    :precondition (and (at ?rover ?waypoint) (at_lander ?lander ?lander_loc) (has-soil-analysis ?rover ?waypoint_data) (visible ?waypoint ?lander_loc) (available ?rover) (channel_free ?lander))
    :effect (and (channel_free ?lander) (communicated_soil_data ?waypoint_data))
  )

  (:action communicate_rock_data
    :parameters (?rover - mobile_unit ?lander - lander ?waypoint_data - waypoint ?waypoint - waypoint ?lander_loc - waypoint)
    :precondition (and (at ?rover ?waypoint) (at_lander ?lander ?lander_loc) (has-rock-analysis ?rover ?waypoint_data) (visible ?waypoint ?lander_loc) (available ?rover) (channel_free ?lander))
    :effect (and (channel_free ?lander) (communicated_rock_data ?waypoint_data))
  )

  (:action communicate_image_data
    :parameters (?rover - mobile_unit ?lander - lander ?waypoint_data - waypoint ?waypoint - waypoint ?objective - objective ?mode - mode)
    :precondition (and (at ?rover ?waypoint) (at_lander ?lander ?waypoint_data) (has-image ?rover ?objective ?mode) (visible ?waypoint ?waypoint_data) (available ?rover) (channel_free ?lander))
    :effect (and (channel_free ?lander) (communicated_image_data ?objective ?mode))
  )

)