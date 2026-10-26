(define (domain Rover)
  (:requirements :strips :typing)
  (:types
    Rover - object
    Waypoint - object
    Store - object
    Camera - object
    Mode - object
    Lander - object
    Objective - object
  )

  (:predicates
    (visible ?w1 ?w2 - Waypoint)
    (at_soil_sample ?w - Waypoint)
    (at_rock_sample ?w - Waypoint)
    (at_lander ?l - Lander ?w - Waypoint)
    (channel_free ?l - Lander)
    (at ?r - Rover ?w - Waypoint)
    (available ?r - Rover)
    (store_of ?s - Store ?r - Rover)
    (empty ?s - Store)
    (full ?s - Store)
    (equipped_for_soil_analysis ?r - Rover)
    (equipped_for_rock_analysis ?r - Rover)
    (equipped_for_imaging ?r - Rover)
    (can_traverse ?r - Rover ?w1 ?w2 - Waypoint)
    (on_board ?c - Camera ?r - Rover)
    (calibration_target ?c - Camera ?o - Objective)
    (supports ?c - Camera ?m - Mode)
    (visible_from ?o - Objective ?w - Waypoint)
    (calibrated ?c - Camera ?r - Rover)
    (has_soil_analysis ?r - Rover ?w - Waypoint)
    (has_rock_analysis ?r - Rover ?w - Waypoint)
    (has_image ?r - Rover ?o - Objective ?m - Mode)
    (communicated_soil_data ?w - Waypoint)
    (communicated_rock_data ?w - Waypoint)
    (communicated_image_data ?o - Objective ?m - Mode)
  )

  (:action navigate
    :parameters (?r - Rover ?from ?to - Waypoint)
    :precondition (and
                    (can_traverse ?r ?from ?to)
                    (available ?r)
                    (at ?r ?from)
                    (visible ?from ?to)
                  )
    :effect (and
              (not (at ?r ?from))
              (at ?r ?to)
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
              (not (empty ?s))
              (full ?s)
              (has_soil_analysis ?r ?w)
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
              (not (empty ?s))
              (full ?s)
              (has_rock_analysis ?r ?w)
              (not (at_rock_sample ?w))
            )
  )

  (:action drop
    :parameters (?r - Rover ?s - Store)
    :precondition (and
                    (store_of ?s ?r)
                    (full ?s)
                  )
    :effect (and
              (not (full ?s))
              (empty ?s)
            )
  )

  (:action calibrate
    :parameters (?r - Rover ?c - Camera ?o - Objective ?w - Waypoint)
    :precondition (and
                    (equipped_for_imaging ?r)
                    (calibration_target ?c ?o)
                    (at ?r ?w)
                    (visible_from ?o ?w)
                    (on_board ?c ?r)
                  )
    :effect (and
              (calibrated ?c ?r)
            )
  )

  (:action take_image
    :parameters (?r - Rover ?w - Waypoint ?o - Objective ?c - Camera ?m - Mode)
    :precondition (and
                    (calibrated ?c ?r)
                    (on_board ?c ?r)
                    (equipped_for_imaging ?r)
                    (supports ?c ?m)
                    (visible_from ?o ?w)
                    (at ?r ?w)
                  )
    :effect (and
              (has_image ?r ?o ?m)
              (not (calibrated ?c ?r))
            )
  )

  (:action communicate_soil_data
    :parameters (?r - Rover ?w1 - Waypoint ?l - Lander ?w2 - Waypoint ?w3 - Waypoint)
    :precondition (and
                    (at ?r ?w1)
                    (at_lander ?l ?w2)
                    (has_soil_analysis ?r ?w3)
                    (visible ?w1 ?w2)
                    (available ?r)
                    (channel_free ?l)
                  )
    :effect (and
              (channel_free ?l)
              (communicated_soil_data ?w3)
              (available ?r)
              (not (available ?r))
              (not (channel_free ?l))
            )
  )

  (:action communicate_rock_data
    :parameters (?r - Rover ?w1 - Waypoint ?l - Lander ?w2 - Waypoint ?w3 - Waypoint)
    :precondition (and
                    (at ?r ?w1)
                    (at_lander ?l ?w2)
                    (has_rock_analysis ?r ?w3)
                    (visible ?w1 ?w2)
                    (available ?r)
                    (channel_free ?l)
                  )
    :effect (and
              (channel_free ?l)
              (communicated_rock_data ?w3)
              (available ?r)
              (not (available ?r))
              (not (channel_free ?l))
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
              (not (available ?r))
              (not (channel_free ?l))
            )
  )
)