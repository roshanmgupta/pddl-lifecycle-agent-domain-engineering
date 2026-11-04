(define (domain driverlog)
  (:requirements :strips :typing)

  (:predicates
    (OBJ ?obj - object)
    (TRUCK ?truck - object)
    (LOCATION ?loc - object)
    (DRIVER ?d - object)
    (at ?obj - object ?loc - object)
    (in ?obj1 - object ?obj - object)
    (driving ?d - object ?v - object)
    (link ?x - object ?y - object)
    (path ?x - object ?y - object)
    (empty ?v - object)
  )

  (:action LOAD-TRUCK
    :parameters (?obj - object ?truck - object ?loc - object)
    :precondition (and (OBJ ?obj) (TRUCK ?truck) (LOCATION ?loc) (at ?truck ?loc) (at ?obj ?loc))
    :effect (and (not (at ?obj ?loc)) (in ?obj ?truck))
  )

  (:action UNLOAD-TRUCK
    :parameters (?obj - object ?truck - object ?loc - object)
    :precondition (and (OBJ ?obj) (TRUCK ?truck) (LOCATION ?loc) (at ?truck ?loc) (in ?obj ?truck))
    :effect (and (not (in ?obj ?truck)) (at ?obj ?loc))
  )

  (:action BOARD-TRUCK
    :parameters (?driver - object ?truck - object ?loc - object)
    :precondition (and (DRIVER ?driver) (TRUCK ?truck) (LOCATION ?loc) (at ?truck ?loc) (at ?driver ?loc) (empty ?truck))
    :effect (and (not (at ?driver ?loc)) (driving ?driver ?truck) (not (empty ?truck)))
  )

  (:action DISEMBARK-TRUCK
    :parameters (?driver - object ?truck - object ?loc - object)
    :precondition (and (DRIVER ?driver) (TRUCK ?truck) (LOCATION ?loc) (at ?truck ?loc) (driving ?driver ?truck))
    :effect (and (not (driving ?driver ?truck)) (at ?driver ?loc) (empty ?truck))
  )

  (:action DRIVE-TRUCK
    :parameters (?truck - object ?loc-from - object ?loc-to - object ?driver - object)
    :precondition (and (TRUCK ?truck) (LOCATION ?loc-from) (LOCATION ?loc-to) (DRIVER ?driver) (at ?truck ?loc-from) (driving ?driver ?truck) (link ?loc-from ?loc-to))
    :effect (and (not (at ?truck ?loc-from)) (at ?truck ?loc-to))
  )

  (:action WALK
    :parameters (?driver - object ?loc-from - object ?loc-to - object)
    :precondition (and (DRIVER ?driver) (LOCATION ?loc-from) (LOCATION ?loc-to) (at ?driver ?loc-from) (path ?loc-from ?loc-to))
    :effect (and (not (at ?driver ?loc-from)) (at ?driver ?loc-to))
  )

)