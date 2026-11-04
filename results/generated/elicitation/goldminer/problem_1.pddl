(define (problem instance-1)
  (:domain goldminer)

  (:objects
    f0-0f f0-1f f1-0f f1-1f - location
    robot1 - robot
    laser1 - laser
    bomb1 - bomb
    gold1 - gold
    soft_rock1 - soft_rock
    hard_rock1 - hard_rock
  )

  (:init
    (arm-empty robot1)
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
    (has-soft-rock f0-1f)
    (has-bomb f1-0f)
    (has-laser f1-0f)
    (clear f1-0f)
    (has-gold f1-1f)
    (has-soft-rock f1-1f)
  )

  (:goal (and (holding robot1 gold)))
)