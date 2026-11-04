(define (domain pipesworld_strips)
  (:requirements :strips :typing)

  (:types
    a area atom b batch-atom pipe product - object
  )

  (:constants
    gasoleo lco rat - a oca1 oc1b
  )

  (:predicates
    (connect ?from - object ?to - object ?pipe - object)
    (unitary ?pipe - object)
    (-unitary ?pipe - object)
    (last ?batch-atom - object ?pipe - object)
    (first ?batch-atom - object ?pipe - object)
    (follow ?next - object ?previous - object)
    (is-product ?batch-atom - object ?product - object)
    (on ?batch-atom - object ?area - object)
    (may-interface ?product-a - object ?product-b - object)
    (normal ?pipe - object)
    (push-updating ?pipe - object)
    (pop-updating ?pipe - object)
  )

  (:action PUSH-START
    :parameters (?pipe - pipe ?batch-atom-in - batch-atom ?from-area - area ?to-area - area ?first-batch-atom - batch-atom ?product-batch-atom-in - product ?product-first-batch - product)
    :precondition (and (normal ?pipe) (first ?first-batch-atom ?pipe) (connect ?from-area ?to-area ?pipe) (on ?batch-atom-in ?from-area) (is-product ?batch-atom-in ?product-batch-atom-in) (is-product ?first-batch-atom ?product-first-batch) (may-interface ?product-batch-atom-in ?product-first-batch))
    :effect (and (push-updating ?pipe) (not (normal ?pipe)) (first ?batch-atom-in ?pipe) (not (first ?first-batch-atom ?pipe)) (follow ?first-batch-atom ?batch-atom-in) (not (on ?batch-atom-in ?from-area)))
  )

  (:action PUSH-END
    :parameters (?pipe - pipe ?from-area - area ?to-area - area ?last-batch-atom - batch-atom ?next-last-batch-atom - batch-atom)
    :precondition (and (push-updating ?pipe) (last ?last-batch-atom ?pipe) (connect ?from-area ?to-area ?pipe) (follow ?last-batch-atom ?next-last-batch-atom))
    :effect (and (not (push-updating ?pipe)) (normal ?pipe) (not (follow ?last-batch-atom ?next-last-batch-atom)) (last ?next-last-batch-atom ?pipe) (not (last ?last-batch-atom ?pipe)) (on ?last-batch-atom ?to-area))
  )

  (:action POP-START
    :parameters (?pipe - pipe ?batch-atom-in - batch-atom ?from-area - area ?to-area - area ?last-batch-atom - batch-atom ?product-batch-atom-in - product ?product-last-batch - product)
    :precondition (and (normal ?pipe) (last ?last-batch-atom ?pipe) (connect ?from-area ?to-area ?pipe) (on ?batch-atom-in ?to-area) (is-product ?batch-atom-in ?product-batch-atom-in) (is-product ?last-batch-atom ?product-last-batch) (may-interface ?product-batch-atom-in ?product-last-batch))
    :effect (and (pop-updating ?pipe) (not (normal ?pipe)) (last ?batch-atom-in ?pipe) (not (last ?last-batch-atom ?pipe)) (follow ?batch-atom-in ?last-batch-atom) (not (on ?batch-atom-in ?to-area)))
  )

  (:action POP-END
    :parameters (?pipe - pipe ?from-area - area ?to-area - area ?first-batch-atom - batch-atom ?next-first-batch-atom - batch-atom)
    :precondition (and (pop-updating ?pipe) (first ?first-batch-atom ?pipe) (connect ?from-area ?to-area ?pipe) (follow ?next-first-batch-atom ?first-batch-atom))
    :effect (and (not (pop-updating ?pipe)) (normal ?pipe) (not (follow ?next-first-batch-atom ?first-batch-atom)) (first ?next-first-batch-atom ?pipe) (not (first ?first-batch-atom ?pipe)) (on ?first-batch-atom ?from-area))
  )

  (:action PUSH-UNITARYPIPE
    :parameters (?pipe - pipe ?batch-atom-in - batch-atom ?from-area - area ?to-area - area ?first-batch-atom - batch-atom ?product-batch-atom-in - product ?product-first-batch - product)
    :precondition (and (first ?first-batch-atom ?pipe) (connect ?from-area ?to-area ?pipe) (on ?batch-atom-in ?from-area) (unitary ?pipe) (is-product ?batch-atom-in ?product-batch-atom-in) (is-product ?first-batch-atom ?product-first-batch) (may-interface ?product-batch-atom-in ?product-first-batch))
    :effect (and (first ?batch-atom-in ?pipe) (not (first ?first-batch-atom ?pipe)) (last ?batch-atom-in ?pipe) (not (last ?first-batch-atom ?pipe)) (not (on ?batch-atom-in ?from-area)) (on ?first-batch-atom ?to-area))
  )

  (:action POP-UNITARYPIPE
    :parameters (?pipe - pipe ?batch-atom-in - batch-atom ?from-area - area ?to-area - area ?last-batch-atom - batch-atom ?product-batch-atom-in - product ?product-last-batch - product)
    :precondition (and (last ?last-batch-atom ?pipe) (connect ?from-area ?to-area ?pipe) (on ?batch-atom-in ?to-area) (unitary ?pipe) (is-product ?batch-atom-in ?product-batch-atom-in) (is-product ?last-batch-atom ?product-last-batch) (may-interface ?product-batch-atom-in ?product-last-batch))
    :effect (and (last ?batch-atom-in ?pipe) (not (last ?last-batch-atom ?pipe)) (first ?batch-atom-in ?pipe) (not (first ?last-batch-atom ?pipe)) (not (on ?batch-atom-in ?to-area)))
  )

)