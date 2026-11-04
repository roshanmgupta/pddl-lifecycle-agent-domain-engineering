(define (domain driverlog)
  (:requirements :strips)

  (:predicates
    (OBJ ?obj)
    (TRUCK ?truck)
    (LOCATION ?loc)
    (DRIVER ?d)
    (at ?obj ?loc)
    (in ?obj1 ?obj)
    (driving ?d ?v)
    (link ?x ?y)
    (path ?x ?y)
    (empty ?v)
  )

  (:action LOAD-TRUCK
    :parameters (?obj ?truck ?loc)
    :precondition (and (OBJ ?obj) (TRUCK ?truck) (LOCATION ?loc) (at ?truck ?loc) (at ?obj ?loc))
    :effect (and (in ?obj ?truck) (not (at ?obj ?loc)))
  )

  (:action UNLOAD-TRUCK
    :parameters (?obj ?truck ?loc)
    :precondition (and (OBJ ?obj) (TRUCK ?truck) (LOCATION ?loc) (at ?truck ?loc) (in ?obj ?truck))
    :effect (and (at ?obj ?loc) (not (in ?obj ?truck)))
  )

  (:action BOARD-TRUCK
    :parameters (?driver ?truck ?loc)
    :precondition (and (DRIVER ?driver) (TRUCK ?truck) (LOCATION ?loc) (at ?truck ?loc) (at ?driver ?loc) (empty ?truck))
    :effect (and (driving ?driver ?truck) (not (at ?driver ?loc)) (not (empty ?truck)))
  )

  (:action DISEMBARK-TRUCK
    :parameters (?driver ?truck ?loc)
    :precondition (and (DRIVER ?driver) (TRUCK ?truck) (LOCATION ?loc) (at ?truck ?loc) (driving ?driver ?truck))
    :effect (and (at ?driver ?loc) (empty ?truck) (not (driving ?driver ?truck)))
  )

  (:action DRIVE-TRUCK
    :parameters (?truck ?loc-from ?loc-to ?driver)
    :precondition (and (TRUCK ?truck) (LOCATION ?loc-from) (LOCATION ?loc-to) (DRIVER ?driver) (at ?truck ?loc-from) (driving ?driver ?truck) (link ?loc-from ?loc-to))
    :effect (and (at ?truck ?loc-to) (not (at ?truck ?loc-from)))
  )

  (:action WALK
    :parameters (?driver ?loc-from ?loc-to)
    :precondition (and (DRIVER ?driver) (LOCATION ?loc-from) (LOCATION ?loc-to) (at ?driver ?loc-from) (path ?loc-from ?loc-to))
    :effect (and (at ?driver ?loc-to) (not (at ?driver ?loc-from)))
  )

)