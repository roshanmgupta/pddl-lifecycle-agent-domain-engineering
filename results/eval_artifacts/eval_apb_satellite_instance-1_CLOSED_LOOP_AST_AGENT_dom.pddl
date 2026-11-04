(define (domain satellite)
  (:requirements :strips :typing)

  (:types
    direction instrument mode satellite - object
  )

  (:predicates
    (on_board ?i - object ?s - object)
    (supports ?i - object ?m - object)
    (pointing ?s - object ?d - object)
    (power_avail ?s - object)
    (power_on ?i - object)
    (calibrated ?i - object)
    (have_image ?d - object ?m - object)
    (calibration_target ?i - object ?d - object)
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
    :effect (and (power_avail ?s) (not (power_on ?i)))
  )

  (:action calibrate
    :parameters (?s - satellite ?i - instrument ?d - direction)
    :precondition (and (on_board ?i ?s) (calibration_target ?i ?d) (pointing ?s ?d) (power_on ?i))
    :effect (calibrated ?i)
  )

  (:action take_image
    :parameters (?s - satellite ?d - direction ?i - instrument ?m - mode)
    :precondition (and (calibrated ?i) (on_board ?i ?s) (supports ?i ?m) (power_on ?i) (pointing ?s ?d))
    :effect (have_image ?d ?m)
  )

)