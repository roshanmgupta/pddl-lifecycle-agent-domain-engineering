(define (domain blocksworld-4ops)
  (:requirements :strips :typing)

  (:predicates
    (clear ?x - object)
    (ontable ?x - object)
    (handempty)
    (holding ?x - object)
    (on ?x - object ?y - object)
    (state_deadlock_mutex_lock)
  )

  (:action pick-up
    :parameters (?ob - object)
    :precondition (and (clear ?ob) (ontable ?ob) (handempty))
    :effect (and (not (clear ?ob)) (not (ontable ?ob)) (not (handempty)) (holding ?ob))
  )

  (:action put-down
    :parameters (?ob - object)
    :precondition (holding ?ob)
    :effect (and (clear ?ob) (handempty) (ontable ?ob) (not (holding ?ob)))
  )

  (:action stack
    :parameters (?ob - object ?underob - object)
    :precondition (and (clear ?underob) (holding ?ob))
    :effect (and (not (clear ?underob)) (on ?ob ?underob) (not (holding ?ob)) (handempty) (clear ?ob))
  )

  (:action unstack
    :parameters (?ob - object ?underob - object)
    :precondition (and (on ?ob ?underob) (clear ?ob) (handempty))
    :effect (and (holding ?ob) (clear ?underob) (not (on ?ob ?underob)) (not (clear ?ob)) (not (handempty)))
  )

)