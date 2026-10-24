(define (problem instance-1)
  (:domain rovers)

  (:objects
    general - general
    mode_high_res mode_low_res - mode_type
    rover0 - rover
    rover0store - storage
    waypoint0 waypoint1 waypoint2 - waypoint
    camera0 - device
    objective0 - objective
    soil_data rock_data image_data - data
    soil-sample rock-sample imaging - object
  )

  (:init
    (visible waypoint0 waypoint1)
    (visible waypoint1 waypoint0)
    (visible waypoint0 waypoint2)
    (visible waypoint2 waypoint0)
    (visible waypoint1 waypoint2)
    (visible waypoint2 waypoint1)
    (at waypoint0 soil-sample)
    (at waypoint1 rock-sample)
    (at waypoint2 soil-sample)
    (at waypoint2 rock-sample)
    (at general waypoint0)
    (channel-free general)
    (at rover0 waypoint0)
    (available rover0)
    (store-of rover0store rover0)
    (equipped-for rover0 mode_high_res)
    (equipped-for rover0 mode_low_res)
    (equipped-for rover0 imaging)
    (on-board camera0 rover0)
    (calibration-target camera0 objective0)
    (supports camera0 mode_high_res)
    (supports camera0 mode_low_res)
    (visible waypoint2 objective0)
  )

  (:goal (and (communicated objective0 soil_data) (communicated objective0 rock_data) (communicated objective0 image_data)))
)