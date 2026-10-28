(define (problem gripper-impossible)
(:domain gripper-strips)
(:objects robot1 - robot
rgripper1 lgripper1 - gripper
room1 room2 - room
ball1 - object)
(:init
(at-robby robot1 room2)
(free robot1 rgripper1)
(free robot1 lgripper1)
(at ball1 room2)
)
(:goal
(and
(free robot1 rgripper1)
(carry robot1 ball1 rgripper1)
)
)
)