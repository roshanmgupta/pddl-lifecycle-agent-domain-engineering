(define (domain satellite)
  (:requirements :strips :typing)
  (:types
    satellite - object
    direction - object
    instrument - object
    mode - object
  )
  (:predicates
    (pointing_at ?s - satellite ?d - direction)
    (on_board ?i - instrument ?s - satellite)
    (power_avail ?s - satellite)
    (power_on ?i - instrument)
    (calibration_target ?i - instrument ?d - direction)
    (calibrated ?i - instrument)
    (supports ?i - instrument ?m - mode)
    (has_image ?d - direction ?m - mode)
  )
  (:action turn
    :parameters (?s - satellite ?from - direction ?to - direction)
    :precondition (and (pointing_at ?s ?from))
    :effect (and
              (pointing_at ?s ?to)
              (not (pointing_at ?s ?from))
            )
  )
  (:action switch_on
    :parameters (?i - instrument ?s - satellite)
    :precondition (and
                    (on_board ?i ?s)
                    (power_avail ?s)
                  )
    :effect (and
              (power_on ?i)
              (not (calibrated ?i))
              (not (power_avail ?s))
            )
  )
  (:action switch_off
    :parameters (?i - instrument ?s - satellite)
    :precondition (and
                    (on_board ?i ?s)
                    (power_on ?i)
                  )
    :effect (and
              (power_avail ?s)
              (not (power_on ?i))
            )
  )
  (:action calibrate
    :parameters (?i - instrument ?s - satellite ?d - direction)
    :precondition (and
                    (on_board ?i ?s)
                    (calibration_target ?i ?d)
                    (pointing_at ?s ?d)
                    (power_on ?i)
                  )
    :effect (and
              (calibrated ?i)
            )
  )
  (:action take_image
    :parameters (?d - direction ?i - instrument ?m - mode ?s - satellite)
    :precondition (and
                    (calibrated ?i)
                    (on_board ?i ?s)
                    (supports ?i ?m)
                    (power_on ?i)
                    (pointing_at ?s ?d)
                  )
    :effect (and
              (has_image ?d ?m)
            )
  )
)