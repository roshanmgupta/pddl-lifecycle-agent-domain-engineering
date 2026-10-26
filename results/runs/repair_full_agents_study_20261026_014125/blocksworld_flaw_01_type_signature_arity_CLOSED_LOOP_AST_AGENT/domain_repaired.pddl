(define (domain blocksworld-4ops)
  (:requirements :strips :typing)

  (:predicates
    (clear ?x - object)
    (ontable ?x - object)
    (handempty)
    (holding ?x - object)
    (on ?x - object ?y - object)
  )

  (:action pick-up
    :parameters (?x - object)
    :precondition (and (clear ?x) (ontable ?x) (handempty))
    :effect (and (holding ?x) (not (ontable ?x)) (not (handempty)) (not (clear ?x)))
  )

  (:action put-down
    :parameters (?x - object)
    :precondition (holding ?x)
    :effect (and (clear ?x) (handempty) (ontable ?x) (not (holding ?x)))
  )

  (:action stack
    :parameters (?x - object ?y - object)
    :precondition (and (clear ?y) (holding ?x))
    :effect (and (handempty) (on ?x ?y) (not (clear ?y)) (not (holding ?x)))
  )

  (:action unstack
    :parameters (?x - object ?y - object)
    :precondition (and (on ?x ?y) (clear ?x) (handempty))
    :effect (and (holding ?x) (clear ?y) (not (on ?x ?y)) (not (handempty)))
  )

)