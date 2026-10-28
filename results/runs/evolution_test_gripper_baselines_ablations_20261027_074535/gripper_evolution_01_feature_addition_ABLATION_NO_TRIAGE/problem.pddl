(define (problem gripper-coop-transfer-discriminative)
(:domain gripper-strips)
(:objects robot1 robot2 - robot
          rgripper1 lgripper1 rgripper2 lgripper2 - gripper
          room1 room2 - room
          ball1 - object)
(:init
    (at-robby robot1 room1)
    (at-robby robot2 room1)
    (carry robot1 ball1 rgripper1)
    (free robot1 lgripper1)
    (free robot2 rgripper2)
    (free robot2 lgripper2)
)
(:goal
    (and
        (carry robot2 ball1 rgripper2)
        (at-robby robot1 room1)
    )
)
)
