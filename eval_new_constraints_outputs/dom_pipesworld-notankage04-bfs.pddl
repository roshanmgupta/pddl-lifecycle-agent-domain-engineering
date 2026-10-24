(define (domain pipesworld-notankage04-bfs)
  (:requirements :strips :typing)

  (:types
    area batch-atom gasoleo lco oc1b oca1 pipe rat-a - object
  )

  (:predicates
    (normal ?p - pipe)
    (may-interface ?x - object ?y - object)
    (connect ?a - area ?b - area ?p - pipe)
    (product-of ?b - batch-atom ?o - object)
    (on ?b - batch-atom ?a - area)
    (first-in ?b - batch-atom ?p - pipe)
    (last-in ?b - batch-atom ?p - pipe)
    (unitary ?p - pipe)
  )

)