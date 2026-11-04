(define (problem gripper_problem)
  (:domain gripper_domain)

  (:objects
    g1 - gripper
    obj1 - object
  )

  (:init
    (free g1)
  )

  (:goal (and (holding g1 obj1)))
)