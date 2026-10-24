(define (domain gripper-strips)
  (:requirements :strips)
  (:predicates
    (at ?obj - object ?room - room)
    (free ?robot - robot ?gripper - gripper)
    (carrying ?robot - robot ?obj - object ?gripper - gripper)
  )

  (:action move
    :parameters (?robot - robot ?from - room ?to - room)
    :precondition (at ?robot ?from)
    :effect (and
      (at ?robot ?to)
      (not (at ?robot ?from))
    )
  )

  (:action pick
    :parameters (?robot - robot ?obj - object ?gripper - gripper ?room - room)
    :precondition (and
      (at ?obj ?room)
      (at ?robot ?room)
      (free ?robot ?gripper)
    )
    :effect (and
      (carrying ?robot ?obj ?gripper)
      (not (at ?obj ?room))
      (not (free ?robot ?gripper))
    )
  )

  (:action drop
    :parameters (?robot - robot ?obj - object ?gripper - gripper ?room - room)
    :precondition (and
      (carrying ?robot ?obj ?gripper)
      (at ?robot ?room)
    )
    :effect (and
      (at ?obj ?room)
      (free ?robot ?gripper)
      (not (carrying ?robot ?obj ?gripper))
    )
  )
)