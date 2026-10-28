(define (domain logistics-strips)
  (:requirements :strips :typing)

  (:types
    airplane city location obj p0 truck - object
    airport - location
  )

  (:predicates
    (specialized_mode_enabled)
    (OBJ ?obj - object)
    (TRUCK ?truck - object)
    (LOCATION ?loc - object)
    (AIRPLANE ?airplane - object)
    (CITY ?city - object)
    (AIRPORT ?airport - object)
    (at ?obj - object ?loc - object)
    (in ?obj1 - object ?obj2 - object)
    (in-city ?loc - object ?city - object)
  )

  (:action load_truck
    :parameters (?obj - object ?truck - truck ?loc - location)
    :precondition (and (OBJ ?obj) (TRUCK ?truck) (LOCATION ?loc) (at ?truck ?loc) (at ?obj ?loc))
    :effect (and (not (at ?obj ?loc)) (in ?obj ?truck))
  )

  (:action load_airplane
    :parameters (?obj - object ?airplane - airplane ?loc - location)
    :precondition (and (OBJ ?obj) (AIRPLANE ?airplane) (LOCATION ?loc) (at ?obj ?loc) (at ?airplane ?loc))
    :effect (and (not (at ?obj ?loc)) (in ?obj ?airplane))
  )

  (:action unload_truck
    :parameters (?obj - object ?truck - truck ?loc - location)
    :precondition (and (OBJ ?obj) (TRUCK ?truck) (LOCATION ?loc) (at ?truck ?loc) (in ?obj ?truck))
    :effect (and (not (in ?obj ?truck)) (at ?obj ?loc))
  )

  (:action unload_airplane
    :parameters (?obj - object ?airplane - airplane ?loc - location)
    :precondition (and (OBJ ?obj) (AIRPLANE ?airplane) (LOCATION ?loc) (in ?obj ?airplane) (at ?airplane ?loc))
    :effect (and (not (in ?obj ?airplane)) (at ?obj ?loc))
  )

  (:action drive_truck
    :parameters (?truck - truck ?loc-from - location ?loc-to - location ?city - city)
    :precondition (and (TRUCK ?truck) (LOCATION ?loc-from) (LOCATION ?loc-to) (CITY ?city) (at ?truck ?loc-from) (in-city ?loc-from ?city) (in-city ?loc-to ?city))
    :effect (and (not (at ?truck ?loc-from)) (at ?truck ?loc-to))
  )

  (:action fly_airplane
    :parameters (?airplane - airplane ?loc-from - airport ?loc-to - airport)
    :precondition (and (AIRPLANE ?airplane) (AIRPORT ?loc-from) (AIRPORT ?loc-to) (at ?airplane ?loc-from))
    :effect (and (not (at ?airplane ?loc-from)) (at ?airplane ?loc-to))
  )

)