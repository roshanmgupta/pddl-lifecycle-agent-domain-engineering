(define (domain satellite)
  (:requirements :strips :typing)

  (:types
    direction instrument mode satellite - object
  )

  (:predicates
    (pointing ?s - satellite ?d - direction)
    (on_board ?i - instrument ?s - satellite)
    (power_avail ?s - satellite)
    (power-on ?i - instrument)
    (calibrated ?i - instrument)
    (supports ?i - instrument ?m - mode)
    (calibration_target ?i - instrument ?d - direction)
    (has-image ?d - direction ?m - mode)
    (have_image ?d - direction ?m - mode)
    (power_avail ?x1 - satellite)
  )

  (:action turn-satellite
    :parameters (?s - satellite ?from - direction ?to - direction)
    :precondition (pointing ?s ?from)
    :effect (and (pointing ?s ?to) (not (pointing ?s ?from)))
  )

  (:action switch-on-instrument
    :parameters (?i - instrument ?s - satellite)
    :precondition (and (on_board ?i ?s) (power_avail ?s))
    :effect (and (power-on ?i) (not (power_avail ?s)))
  )

  (:action switch-off-instrument
    :parameters (?i - instrument ?s - satellite)
    :precondition (and (on_board ?i ?s) (power-on ?i))
    :effect (and (not (power-on ?i)) (power_avail ?s))
  )

  (:action calibrate-instrument
    :parameters (?i - instrument ?s - satellite ?d - direction)
    :precondition (and (on_board ?i ?s) (calibration_target ?i ?d) (pointing ?s ?d) (power-on ?i))
    :effect (calibrated ?i)
  )

  (:action take-image
    :parameters (?s - satellite ?d - direction ?i - instrument ?m - mode)
    :precondition (and (calibrated ?i) (on_board ?i ?s) (supports ?i ?m) (power-on ?i) (pointing ?s ?d))
    :effect (and (has-image ?d ?m) (not (calibrated ?i)) (have_image ?d ?m))
  )

)