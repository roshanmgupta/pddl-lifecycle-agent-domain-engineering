(define (domain blocksworld-4ops)
  (:requirements :strips :typing)

  (:types
    block - object
  )

  (:predicates
    (clear ?x - object)
    (ontable ?x - object)
    (handempty)
    (holding ?x - block)
    (on ?x - object ?y - object)
  )

  (:action pick-up
    :parameters (?ob - block)
    :precondition (and (clear ?ob) (ontable ?ob) (handempty))
    :effect (and (holding ?ob) (not (clear ?ob)) (not (ontable ?ob)) (not (handempty)))
  )

  (:action put-down
    :parameters (?ob - block)
    :precondition (holding ?ob)
    :effect (and (clear ?ob) (handempty) (ontable ?ob) (not (holding ?ob)))
  )

  (:action stack
    :parameters (?ob - block ?underob - block)
    :precondition (and (clear ?underob) (holding ?ob))
    :effect (and (handempty) (clear ?ob) (on ?ob ?underob) (not (clear ?underob)) (not (holding ?ob)))
  )

  (:action unstack
    :parameters (?ob - block ?underob - block)
    :precondition (and (on ?ob ?underob) (clear ?ob) (handempty))
    :effect (and (holding ?ob) (clear ?underob) (not (on ?ob ?underob)) (not (clear ?ob)) (not (handempty)))
  )

)