(define (problem blocksworld_problem)
  (:domain blocksworld)

  (:objects
    A - block
    B - block
    C - block
    table - table
  )

  (:init
    (on A B)
    (on B table)
    (on C table)
    (clear A)
    (clear C)
    (emptyhand)
  )

  (:goal (and (on C B) (on B A)))
)