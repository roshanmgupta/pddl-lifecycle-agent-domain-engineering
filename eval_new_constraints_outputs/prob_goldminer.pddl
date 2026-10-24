(define (problem instance-1)
  (:domain goldminer)

  (:objects
    robot1 - robot
    f0-0f f0-1f f1-0f f1-1f - location
    gold1 - gold
    soft-rock1 - soft-rock
    bomb1 - bomb
    laser1 - laser
  )

  (:init
    (empty-arm robot1)
    (connected f0-0f f0-1f)
    (connected f1-0f f1-1f)
    (connected f0-0f f1-0f)
    (connected f0-1f f1-1f)
    (connected f0-1f f0-0f)
    (connected f1-1f f1-0f)
    (connected f1-0f f0-0f)
    (connected f1-1f f0-1f)
    (at robot1 f0-0f)
    (clear f0-0f)
    (at soft-rock1 f0-1f)
    (at bomb1 f1-0f)
    (at laser1 f1-0f)
    (clear f1-0f)
    (at gold1 f1-1f)
    (at soft-rock1 f1-1f)
  )

  (:goal (and (holding robot1 gold1)))
)