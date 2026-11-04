(define (problem gripper_problem)
  (:domain gripper_domain)

  (:objects
    r1 - robot
    room_a - room
    room_b - room
    door_ab - doorway
  )

  (:init
    (at r1 room_a)
    (connected room_a room_b door_ab)
  )

  (:goal (and (at r1 room_b)))
)