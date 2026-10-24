(define (domain satellite)
  (:requirements :strips :typing)

  (:types
    direction instrument mode satellite - object
  )

  (:predicates
    (supports ?i - instrument ?m - mode)
    (calibration-target ?i - instrument ?gs - direction)
    (on-board ?i - instrument ?s - satellite)
    (power-available ?s - satellite)
    (pointing-at ?s - satellite ?d - direction)
    (has-image ?d - direction ?m - mode)
  )

  (:action capture_image
    :parameters (?i - instrument ?s - satellite ?m - mode ?d - direction ?d1 - direction)
    :precondition (and (supports ?i ?m) (calibration-target ?i ?d1) (on-board ?i ?s) (power-available ?s) (pointing-at ?s ?d))
    :effect (has-image ?d ?m)
  )

)