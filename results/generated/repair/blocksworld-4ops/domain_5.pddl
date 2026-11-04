(define (domain blocksworld-4ops)
  (:requirements :strips :typing)

  (:types
  )

  (:predicates
    (clear ?x)
    (ontable ?x)
    (handempty)
    (holding ?x)
    (on ?x ?y)
    (ontable-object ?ob - object)
    (picked-up ?ob - object)
  )

  (:action pick-up
    :parameters (?ob - object)
    :precondition (and (clear ?ob) (ontable-object ?ob) (handempty))
    :effect (and (holding ?ob) (not (clear ?ob)) (not (ontable-object ?ob)) (not (handempty)) (picked-up ?ob))
  )

  (:action put-down
    :parameters (?ob - object)
    :precondition (and (holding ?ob) (picked-up ?ob))
    :effect (and (clear ?ob) (handempty) (ontable-object ?ob) (not (holding ?ob)) (not (picked-up ?ob)))
  )

  (:action stack
    :parameters (?ob - object ?underob - object)
    :precondition (and (clear ?underob) (holding ?ob))
    :effect (and (handempty) (clear ?ob) (on ?ob ?underob) (not (clear ?underob)) (not (holding ?ob)))
  )

  (:action unstack
    :parameters (?ob - object ?underob - object)
    :precondition (and (on ?ob ?underob) (clear ?ob) (handempty))
    :effect (and (holding ?ob) (clear ?underob) (not (on ?ob ?underob)) (not (clear ?ob)) (not (handempty)))
  )

)