(define (domain satellite)
  (:requirements :strips)
  (:predicates
    (supports ?instrument - instrument ?mode - mode)
    (calibration_target ?instrument - instrument ?direction - direction)
    (on_board ?instrument - instrument ?satellite - satellite)
    (power_avail ?satellite - satellite)
    (pointing ?satellite - satellite ?direction - direction)
    (have_image ?direction - direction ?mode - mode)
    (calibrated ?instrument - instrument)
    (power_on ?instrument - instrument)
  )

  (:action turn_satellite
    :parameters (?satellite - satellite ?from_direction - direction ?to_direction - direction)
    :precondition (pointing ?satellite ?from_direction)
    :effect (and
      (pointing ?satellite ?to_direction)
      (not (pointing ?satellite ?from_direction))
    )
  )

  (:action switch_on_instrument
    :parameters (?instrument - instrument ?satellite - satellite)
    :precondition (and (on_board ?instrument ?satellite) (power_avail ?satellite))
    :effect (and
      (power_on ?instrument)
      (not (calibrated ?instrument))
      (not (power_avail ?satellite))
    )
  )

  (:action switch_off_instrument
    :parameters (?instrument - instrument ?satellite - satellite)
    :precondition (and (on_board ?instrument ?satellite) (power_on ?instrument))
    :effect (and
      (not (power_on ?instrument))
      (power_avail ?satellite)
    )
  )

  (:action calibrate_instrument
    :parameters (?instrument - instrument ?satellite - satellite ?direction - direction)
    :precondition (and (on_board ?instrument ?satellite) (calibration_target ?instrument ?direction) (pointing ?satellite ?direction) (power_on ?instrument))
    :effect (calibrated ?instrument)
  )

  (:action take_image
    :parameters (?satellite - satellite ?direction - direction ?instrument - instrument ?mode - mode)
    :precondition (and (calibrated ?instrument) (on_board ?instrument ?satellite) (supports ?instrument ?mode) (power_on ?instrument) (pointing ?satellite ?direction))
    :effect (have_image ?direction ?mode)
  )
)