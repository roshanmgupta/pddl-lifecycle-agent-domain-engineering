(define (domain satellite)
  (:requirements :strips)
  (:types satellite instrument direction mode - object)
  
  (:predicates
    (supports ?i - instrument ?m - mode)
    (calibration_target ?i - instrument ?d - direction)
    (on_board ?i - instrument ?s - satellite)
    (power_avail ?s - satellite)
    (pointing ?s - satellite ?d - direction)
    (power_on ?i - instrument)
    (calibrated ?i - instrument)
    (have_image ?d - direction ?m - mode)
  )
  
  (:action turn
    :parameters (?s - satellite ?from - direction ?to - direction)
    :precondition (and (pointing ?s ?from))
    :effect (and (pointing ?s ?to) (not (pointing ?s ?from)))
  )
  
  (:action switch_on
    :parameters (?i - instrument ?s - satellite)
    :precondition (and (on_board ?i ?s) (power_avail ?s))
    :effect (and (power_on ?i) (not (power_avail ?s)) (not (calibrated ?i)))
  )
  
  (:action switch_off
    :parameters (?i - instrument ?s - satellite)
    :precondition (and (on_board ?i ?s) (power_on ?i))
    :effect (and (power_avail ?s) (not (power_on ?i)))
  )
  
  (:action calibrate
    :parameters (?s - satellite ?i - instrument ?d - direction)
    :precondition (and (on_board ?i ?s)
                       (calibration_target ?i ?d)
                       (pointing ?s ?d)
                       (power_on ?i))
    :effect (and (calibrated ?i))
  )
  
  (:action take_image
    :parameters (?s - satellite ?d - direction ?i - instrument ?m - mode)
    :precondition (and (calibrated ?i)
                       (on_board ?i ?s)
                       (supports ?i ?m)
                       (power_on ?i)
                       (pointing ?s ?d))
    :effect (and (have_image ?d ?m))
  )
)