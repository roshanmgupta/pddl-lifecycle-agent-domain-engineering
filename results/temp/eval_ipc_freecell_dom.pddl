(define (domain freecell)
  (:requirements :strips :typing)

  (:types
    card num suit - object
  )

  (:predicates
    (ON ?c1 - object ?c2 - object)
    (incell ?c - object)
    (CLEAR ?c - object)
    (CELLSPACE ?n - object)
    (COLSPACE ?n - object)
    (HOME ?c - object)
    (BOTTOMCOL ?c - object)
    (CANSTACK ?c1 - object ?c2 - object)
    (SUIT ?c - object ?s - object)
    (VALUE ?c - object ?v - object)
    (SUCCESSOR ?n1 - object ?n0 - object)
  )

  (:action move
    :parameters (?card - card ?oldcard - card ?newcard - card)
    :precondition (and (ON ?card ?oldcard) (CLEAR ?card) (CANSTACK ?card ?newcard) (CLEAR ?newcard))
    :effect (and (not (ON ?card ?oldcard)) (ON ?card ?newcard) (CLEAR ?oldcard) (not (CLEAR ?newcard)))
  )

  (:action move-b
    :parameters (?card - card ?newcard - card ?cols - num ?ncols - num)
    :precondition (and (BOTTOMCOL ?card) (CLEAR ?card) (CANSTACK ?card ?newcard) (CLEAR ?newcard) (COLSPACE ?cols) (SUCCESSOR ?ncols ?cols))
    :effect (and (not (BOTTOMCOL ?card)) (ON ?card ?newcard) (CLEAR ?newcard) (not (COLSPACE ?cols)) (COLSPACE ?ncols))
  )

  (:action sendtofree
    :parameters (?card - card ?oldcard - card ?cells - num ?ncells - num)
    :precondition (and (ON ?card ?oldcard) (CLEAR ?card) (CELLSPACE ?cells) (SUCCESSOR ?ncells ?cells))
    :effect (and (not (ON ?card ?oldcard)) (incell ?card) (CLEAR ?oldcard) (not (CELLSPACE ?cells)) (CELLSPACE ?ncells))
  )

  (:action sendtofree-b
    :parameters (?card - card ?cells - num ?ncells - num ?cols - num ?ncols - num)
    :precondition (and (BOTTOMCOL ?card) (CLEAR ?card) (CELLSPACE ?cells) (SUCCESSOR ?ncells ?cells) (COLSPACE ?cols) (SUCCESSOR ?ncols ?cols))
    :effect (and (not (BOTTOMCOL ?card)) (incell ?card) (not (CELLSPACE ?cells)) (CELLSPACE ?ncells) (not (COLSPACE ?cols)) (COLSPACE ?ncols))
  )

  (:action sendtonewcol
    :parameters (?card - card ?oldcard - card ?cols - num ?ncols - num)
    :precondition (and (ON ?card ?oldcard) (CLEAR ?card) (COLSPACE ?cols) (SUCCESSOR ?ncols ?cols))
    :effect (and (not (ON ?card ?oldcard)) (BOTTOMCOL ?card) (CLEAR ?oldcard) (not (COLSPACE ?cols)) (COLSPACE ?ncols))
  )

  (:action sendtohome
    :parameters (?card - card ?oldcard - card ?suit - suit ?vcard - num ?homecard - card ?vhomecard - num)
    :precondition (and (ON ?card ?oldcard) (CLEAR ?card) (SUIT ?card ?suit) (VALUE ?card ?vcard) (HOME ?homecard) (VALUE ?homecard ?vhomecard) (SUCCESSOR ?vcard ?vhomecard))
    :effect (and (not (ON ?card ?oldcard)) (HOME ?card) (CLEAR ?oldcard) (not (HOME ?homecard)))
  )

  (:action sendtohome-b
    :parameters (?card - card ?suit - suit ?vcard - num ?homecard - card ?vhomecard - num ?cols - num ?ncols - num)
    :precondition (and (BOTTOMCOL ?card) (CLEAR ?card) (SUIT ?card ?suit) (VALUE ?card ?vcard) (HOME ?homecard) (SUIT ?homecard ?suit) (VALUE ?homecard ?vhomecard) (SUCCESSOR ?vcard ?vhomecard) (COLSPACE ?cols) (SUCCESSOR ?ncols ?cols))
    :effect (and (not (BOTTOMCOL ?card)) (HOME ?card) (not (HOME ?homecard)) (not (COLSPACE ?cols)) (COLSPACE ?ncols))
  )

  (:action homefromfreecell
    :parameters (?card - card ?suit - suit ?vcard - num ?homecard - card ?vhomecard - num ?cells - num ?ncells - num)
    :precondition (and (incell ?card) (SUIT ?card ?suit) (VALUE ?card ?vcard) (HOME ?homecard) (VALUE ?homecard ?vhomecard) (SUCCESSOR ?vcard ?vhomecard) (CELLSPACE ?cells) (SUCCESSOR ?ncells ?cells))
    :effect (and (not (incell ?card)) (HOME ?card) (not (HOME ?homecard)) (not (CELLSPACE ?cells)) (CELLSPACE ?ncells))
  )

  (:action colfromfreecell
    :parameters (?card - card ?newcard - card ?cells - num ?ncells - num)
    :precondition (and (incell ?card) (CLEAR ?newcard) (CANSTACK ?card ?newcard) (CELLSPACE ?cells) (SUCCESSOR ?ncells ?cells))
    :effect (and (not (incell ?card)) (ON ?card ?newcard) (CLEAR ?newcard) (not (CELLSPACE ?cells)) (CELLSPACE ?ncells))
  )

  (:action newcolfromfreecell
    :parameters (?card - card ?cols - num ?ncols - num ?cells - num ?ncells - num)
    :precondition (and (incell ?card) (COLSPACE ?cols) (SUCCESSOR ?ncols ?cols) (CELLSPACE ?cells) (SUCCESSOR ?ncells ?cells))
    :effect (and (not (incell ?card)) (BOTTOMCOL ?card) (not (COLSPACE ?cols)) (COLSPACE ?ncols) (not (CELLSPACE ?cells)) (CELLSPACE ?ncells))
  )

)