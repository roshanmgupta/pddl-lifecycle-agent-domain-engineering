(define (domain logistics-strips)
  (:requirements :strips :typing)

  (:types
    airplane city location obj truck - object
    airport l - location
    a p - obj
    c - city
    t - truck
  )

  (:predicates
    (unreachable_precondition_clause)
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

  (:action LOAD-TRUCK
    :parameters (?obj - obj ?truck - truck ?loc - location)
    :precondition (and (OBJ ?obj) (TRUCK ?truck) (LOCATION ?loc) (at ?truck ?loc) (at ?obj ?loc))
    :effect (and (not (at ?obj ?loc)) (in ?obj ?truck))
  )

  (:action LOAD-AIRPLANE
    :parameters (?obj - obj ?airplane - airplane ?loc - location)
    :precondition (and (OBJ ?obj) (AIRPLANE ?airplane) (LOCATION ?loc) (at ?obj ?loc) (at ?airplane ?loc))
    :effect (and (not (at ?obj ?loc)) (in ?obj ?airplane))
  )

  (:action UNLOAD-TRUCK
    :parameters (?obj - obj ?truck - truck ?loc - location)
    :precondition (and (OBJ ?obj) (TRUCK ?truck) (LOCATION ?loc) (at ?truck ?loc) (in ?obj ?truck))
    :effect (and (not (in ?obj ?truck)) (at ?obj ?loc))
  )

  (:action UNLOAD-AIRPLANE
    :parameters (?obj - obj ?airplane - airplane ?loc - location)
    :precondition (and (OBJ ?obj) (AIRPLANE ?airplane) (LOCATION ?loc) (in ?obj ?airplane) (at ?airplane ?loc))
    :effect (and (not (in ?obj ?airplane)) (at ?obj ?loc))
  )

  (:action DRIVE-TRUCK
    :parameters (?truck - truck ?loc-from - location ?loc-to - location ?city - city)
    :precondition (and (TRUCK ?truck) (LOCATION ?loc-from) (LOCATION ?loc-to) (CITY ?city) (at ?truck ?loc-from) (in-city ?loc-from ?city) (in-city ?loc-to ?city))
    :effect (and (not (at ?truck ?loc-from)) (at ?truck ?loc-to))
  )

  (:action FLY-AIRPLANE
    :parameters (?airplane - airplane ?loc-from - airport ?loc-to - airport)
    :precondition (and (AIRPLANE ?airplane) (AIRPORT ?loc-from) (AIRPORT ?loc-to) (at ?airplane ?loc-from))
    :effect (and (not (at ?airplane ?loc-from)) (at ?airplane ?loc-to))
  )

)