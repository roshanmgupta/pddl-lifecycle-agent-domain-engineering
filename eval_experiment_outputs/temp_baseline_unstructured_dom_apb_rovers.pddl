(define (domain Rover)
  (:requirements :strips :typing)
  (:types
    Rover Lander Store Waypoint Camera Mode Objective
  )
  
  (:predicates
    (at ?r - Rover ?w - Waypoint)
    (available ?r - Rover)
    (empty ?s - Store)
    (full ?s - Store)
    (equipped_for_soil_analysis ?r - Rover)
    (equipped_for_rock_analysis ?r - Rover)
    (equipped_for_imaging ?r - Rover)
    (can_traverse ?r - Rover ?w1 - Waypoint ?w2 - Waypoint)
    (on_board ?c - Camera ?r - Rover)
    (calibration_target ?c - Camera ?o - Objective)
    (supports ?c - Camera ?m - Mode)
    (visible ?w1 - Waypoint ?w2 - Waypoint)
    (at_soil_sample ?w - Waypoint)
    (at_rock_sample ?w - Waypoint)
    (at_lander ?l - Lander ?w - Waypoint)
    (channel_free ?l - Lander)
    (visible_from ?o - Objective ?w - Waypoint)
    (communicated_soil_data ?w - Waypoint)
    (communicated_rock_data ?w - Waypoint)
    (communicated_image_data ?o - Objective ?m - Mode)
    (calibrated_to ?c - Camera ?r - Rover)
    (has_soil_analysis ?r - Rover ?w - Waypoint)
    (has_rock_analysis ?r - Rover ?w - Waypoint)
    (has_image ?r - Rover ?o - Objective ?m - Mode)
  )

  (:action navigate
    :parameters (?r - Rover ?w1 - Waypoint ?w2 - Waypoint)
    :precondition (and
      (can_traverse ?r ?w1 ?w2)
      (available ?r)
      (at ?r ?w1)
      (visible ?w1 ?w2)
    )
    :effect (and
      (at ?r ?w2)
      (not (at ?r ?w1))
    )
  )

  (:action sample_soil
    :parameters (?r - Rover ?w - Waypoint ?s - Store)
    :precondition (and
      (at ?r ?w)
      (at_soil_sample ?w)
      (equipped_for_soil_analysis ?r)
      (store_of ?s ?r)
      (empty ?s)
    )
    :effect (and
      (full ?s)
      (has_soil_analysis ?r ?w)
      (not (empty ?s))
      (not (at_soil_sample ?w))
    )
  )

  (:action sample_rock
    :parameters (?r - Rover ?w - Waypoint ?s - Store)
    :precondition (and
      (at ?r ?w)
      (at_rock_sample ?w)
      (equipped_for_rock_analysis ?r)
      (store_of ?s ?r)
      (empty ?s)
    )
    :effect (and
      (full ?s)
      (has_rock_analysis ?r ?w)
      (not (empty ?s))
      (not (at_rock_sample ?w))
    )
  )

  (:action drop_contents
    :parameters (?r - Rover ?s - Store)
    :precondition (and
      (store_of ?s ?r)
      (full ?s)
    )
    :effect (and
      (empty ?s)
      (not (full ?s))
    )
  )

  (:action calibrate
    :parameters (?r - Rover ?c - Camera ?o - Objective ?w - Waypoint)
    :precondition (and
      (equipped_for_imaging ?r)
      (calibration_target ?c ?o)
      (at ?r ?w)
      (visible ?o ?w)
      (on_board ?c ?r)
    )
    :effect (calibrated_to ?c ?r)
  )

  (:action take_image
    :parameters (?r - Rover ?w - Waypoint ?o - Objective ?c - Camera ?m - Mode)
    :precondition (and
      (calibrated_to ?c ?r)
      (on_board ?c ?r)
      (equipped_for_imaging ?r)
      (supports ?c ?m)
      (visible ?o ?w)
      (at ?r ?w)
    )
    :effect (and
      (has_image ?r ?o ?m)
      (not (calibrated_to ?c ?r))
    )
  )

  (:action communicate_soil_data
    :parameters (?r - Rover ?w1 - Waypoint ?l - Lander ?w2 - Waypoint)
    :precondition (and
      (at ?r ?w1)
      (at_lander ?l ?w2)
      (has_soil_analysis ?r ?w1)
      (visible ?w1 ?w2)
      (available ?r)
      (channel_free ?l)
    )
    :effect (and
      (channel_free ?l)
      (communicated_soil_data ?w1)
      (available ?r)
    )
  )

  (:action communicate_rock_data
    :parameters (?r - Rover ?w1 - Waypoint ?l - Lander ?w2 - Waypoint)
    :precondition (and
      (at ?r ?w1)
      (at_lander ?l ?w2)
      (has_rock_analysis ?r ?w1)
      (visible ?w1 ?w2)
      (available ?r)
      (channel_free ?l)
    )
    :effect (and
      (channel_free ?l)
      (communicated_rock_data ?w1)
      (available ?r)
    )
  )

  (:action communicate_image_data
    :parameters (?r - Rover ?w1 - Waypoint ?l - Lander ?w2 - Waypoint ?o - Objective ?m - Mode)
    :precondition (and
      (at ?r ?w1)
      (at_lander ?l ?w2)
      (has_image ?r ?o ?m)
      (visible ?w1 ?w2)
      (available ?r)
      (channel_free ?l)
    )
    :effect (and
      (channel_free ?l)
      (communicated_image_data ?o ?m)
      (available ?r)
    )
  )
)