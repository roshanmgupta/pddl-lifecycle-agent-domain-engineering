(define (domain rovers)
  (:requirements :strips :typing)

  (:types
    data device entity general mode_type objective rover storage waypoint - object
  )

  (:predicates
    (visible ?x - object ?y - object)
    (at ?x - object ?y - object)
    (channel-free ?x - general)
    (available ?x - rover)
    (store-of ?s - storage ?r - rover)
    (equipped-for ?r - rover ?m - object)
    (on-board ?c - device ?r - rover)
    (supports ?c - device ?m - mode_type)
    (communicated ?o - objective ?d - data)
    (calibration-target ?c - device ?o - objective)
  )

  (:action traverse_waypoint
    :parameters (?r - rover ?from - waypoint ?to - waypoint)
    :precondition (and (at ?r ?from) (visible ?from ?to) (available ?r))
    :effect (and (not (at ?r ?from)) (at ?r ?to))
  )

  (:action communicate_data
    :parameters (?r - rover ?o - objective ?d - data ?w - object)
    :precondition (and (at ?r ?w) (visible ?w ?o))
    :effect (communicated ?o ?d)
  )

)