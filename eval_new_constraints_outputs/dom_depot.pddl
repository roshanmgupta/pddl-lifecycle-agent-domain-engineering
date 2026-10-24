(define (domain depot)
  (:requirements :strips :typing)

  (:types
    crate depot mechanical-device pallet physical-item vehicle - object
    distributor - physical-item
    truck - vehicle
    hoist - mechanical-device
  )

  (:predicates
    (at ?x - object ?y - depot)
    (clear ?x - object)
    (available ?x - hoist)
    (on ?x - object ?y - object)
  )

)