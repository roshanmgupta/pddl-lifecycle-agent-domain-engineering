(define (problem instance-1)
  (:domain floortile)

  (:objects
    tile_0-1 tile_0-2 tile_1-1 tile_1-2 tile_2-1 tile_2-2 - tile
    robot1 robot2 - robot
    white black - color
  )

  (:init
    (at robot1 tile_1-2)
    (has-color robot1 white)
    (at robot2 tile_1-1)
    (has-color robot2 black)
    (available-color white)
    (available-color black)
    (clear tile_0-1)
    (clear tile_0-2)
    (clear tile_1-1)
    (clear tile_1-2)
    (clear tile_2-1)
    (clear tile_2-2)
    (up tile_1-1 tile_0-1)
    (up tile_1-2 tile_0-2)
    (up tile_2-1 tile_1-1)
    (up tile_2-2 tile_1-2)
    (down tile_0-1 tile_1-1)
    (down tile_0-2 tile_1-2)
    (down tile_1-1 tile_2-1)
    (down tile_1-2 tile_2-2)
    (to-the-right tile_0-1 tile_0-2)
    (to-the-right tile_1-1 tile_1-2)
    (to-the-right tile_2-1 tile_2-2)
    (to-the-left tile_0-2 tile_0-1)
    (to-the-left tile_1-2 tile_1-1)
    (to-the-left tile_2-2 tile_2-1)
  )

  (:goal (and (painted tile_1-1 white) (painted tile_1-2 black) (painted tile_2-1 black) (painted tile_2-2 white)))
)