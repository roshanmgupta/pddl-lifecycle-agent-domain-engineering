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
    (calibration_target ?i - instrument ?calibration_target_d - direction)
    (supports ?i - instrument ?m - mode)
    (has-image ?s - satellite ?d - direction ?m - mode)
    (have_image ?d - direction ?m - mode)
    (calibrated ?i - instrument)
  )

  (:action turn-satellite
    :parameters (?s - satellite ?from - direction ?to - direction)
    :precondition (pointing ?s ?from)
    :effect (and (pointing ?s ?to) (not (pointing ?s ?from)))
  )

  (:action switch-on-instrument
    :parameters (?i - instrument ?s - satellite)
    :precondition (and (on_board ?i ?s) (power_avail ?s))
    :effect (and (power-on ?i) (not (calibrated ?i)) (not (power_avail ?s)))
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
    :precondition (and (calibration_target ?i ?d) (on_board ?i ?s) (supports ?i ?m) (power-on ?i) (pointing ?s ?d))
    :effect (and (has-image ?s ?d ?m) (have_image ?d ?m))
  )

)