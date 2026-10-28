(define (domain satellite)
  (:requirements :strips :typing)

  (:types
    direction instrument mode satellite - object
  )

  (:predicates
    (on_board ?i - instrument ?s - satellite)
    (supports ?i - instrument ?m - mode)
    (pointing ?s - satellite ?d - direction)
    (power_avail ?s - satellite)
    (power_on ?i - instrument)
    (calibrated ?i - instrument)
    (have_image ?d - direction ?m - mode)
    (calibration_target ?i - instrument ?d - direction)
    (ready_for_calibration ?i - instrument)
    (ready_for_imaging ?i - instrument)
  )

  (:action turn_to
    :parameters (?s - satellite ?d_new - direction ?d_prev - direction)
    :precondition (pointing ?s ?d_prev)
    :effect (and (pointing ?s ?d_new) (not (pointing ?s ?d_prev)))
  )

  (:action switch_on
    :parameters (?i - instrument ?s - satellite)
    :precondition (and (on_board ?i ?s) (power_avail ?s))
    :effect (and (power_on ?i) (not (calibrated ?i)) (not (power_avail ?s)))
  )

  (:action switch_off
    :parameters (?i - instrument ?s - satellite)
    :precondition (and (on_board ?i ?s) (power_on ?i))
    :effect (and (not (power_on ?i)) (power_avail ?s))
  )

  (:action calibrate
    :parameters (?s - satellite ?i - instrument ?d - direction)
    :precondition (and (on_board ?i ?s) (calibration_target ?i ?d) (pointing ?s ?d) (power_on ?i) (ready_for_calibration ?i))
    :effect (and (calibrated ?i) (not (ready_for_calibration ?i)) (ready_for_imaging ?i))
  )

  (:action take_image
    :parameters (?s - satellite ?d - direction ?i - instrument ?m - mode)
    :precondition (and (calibrated ?i) (on_board ?i ?s) (supports ?i ?m) (power_on ?i) (pointing ?s ?d) (ready_for_imaging ?i))
    :effect (and (have_image ?d ?m) (not (ready_for_imaging ?i)))
  )

  (:action prepare_for_calibration
    :parameters (?i - instrument ?s - satellite)
    :precondition (and (on_board ?i ?s) (power_on ?i))
    :effect (ready_for_calibration ?i)
  )

  (:action prepare_for_imaging
    :parameters (?i - instrument ?s - satellite)
    :precondition (and (on_board ?i ?s) (power_on ?i) (calibrated ?i))
    :effect (ready_for_imaging ?i)
  )

)